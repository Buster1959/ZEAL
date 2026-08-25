"""Home Assistant adapter for ZEAL's deterministic schedule engine."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import event as event_helper
from homeassistant.util import dt as dt_util

from ..coordinator import ZealCoordinator
from .audit import AuditLog
from .engine import active_period_at, next_transition_after
from .models import ScheduleConfiguration
from .overrides import TemporaryOverride, create_temporary_overrides

_LOGGER = logging.getLogger(__name__)


class ScheduleRuntime:
    """Apply room schedules only through ZEAL's canonical setpoint boundary."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ZealCoordinator,
        audit_log: AuditLog | None = None,
    ) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._audit_log = audit_log
        self._configuration = ScheduleConfiguration.empty()
        self._cancel_next: Callable[[], None] | None = None
        self._unsub_coordinator: Callable[[], None] | None = None
        self._applied_periods: dict[str, tuple[datetime, str]] = {}
        self._overrides: dict[str, TemporaryOverride] = {}
        self._started = False

    @property
    def configuration(self) -> ScheduleConfiguration:
        """Expose the immutable current document to later UI/API layers."""
        return self._configuration

    async def async_start(self, configuration: ScheduleConfiguration) -> None:
        """Reconcile active targets immediately and arrange the next change."""
        if self._started:
            await self.async_set_configuration(configuration)
            return
        self._started = True
        self._unsub_coordinator = self._coordinator.async_add_listener(
            self._handle_coordinator_update
        )
        await self.async_set_configuration(
            configuration, cause="startup_reconciliation"
        )

    async def async_stop(self) -> None:
        """Cancel timers/listeners and discard ephemeral applied markers."""
        self._started = False
        self._cancel_pending_transition()
        if self._unsub_coordinator is not None:
            self._unsub_coordinator()
            self._unsub_coordinator = None
        self._applied_periods.clear()
        self._overrides.clear()

    async def async_set_configuration(
        self,
        configuration: ScheduleConfiguration,
        *,
        cause: str = "configuration_saved",
    ) -> None:
        """Replace the document, apply current periods and reset the timer."""
        self._configuration = configuration
        self._overrides = {
            room_id: override
            for room_id, override in self._overrides.items()
            if room_id in configuration.rooms
        }
        self._applied_periods.clear()
        self._cancel_pending_transition()
        now = dt_util.now()
        await self._async_apply_active_periods(now, cause=cause)
        self._schedule_next_transition(now)

    def _cancel_pending_transition(self) -> None:
        if self._cancel_next is not None:
            self._cancel_next()
            self._cancel_next = None

    async def _async_apply_active_periods(
        self, now: datetime, *, cause: str
    ) -> None:
        applied_any = False
        for room in self._configuration.rooms.values():
            active = active_period_at(room, now)
            override = self._overrides.get(room.room_id)
            override_expired = False
            if override is not None and override.expires_at <= now:
                self._overrides.pop(room.room_id, None)
                override = None
                override_expired = True
            if active is None and override is None:
                continue
            key = (
                (override.expires_at, f"override:{override.temperature}")
                if override is not None
                else (active.starts_at, active.period.id)
            )
            if self._applied_periods.get(room.room_id) == key:
                continue
            temperature = (
                override.temperature
                if override is not None
                else active.period.temperature
            )
            room_cause = "temporary_override_expired" if override_expired else cause
            thermostat = getattr(self._coordinator, "room_thermostats", {}).get(
                room.room_id
            )
            previous = getattr(thermostat, "target_temperature", None)
            previous_temperature = (
                float(previous)
                if isinstance(previous, (int, float)) and not isinstance(previous, bool)
                else None
            )
            applied = await self._coordinator.async_set_room_target(
                room.room_id,
                temperature,
                source=room_cause,
            )
            if self._audit_log is not None:
                await self._audit_log.async_record(
                    timestamp=now,
                    room_id=room.room_id,
                    room_name=room.room_name,
                    canonical_entity_id=getattr(thermostat, "entity_id", None),
                    previous_temperature=previous_temperature,
                    requested_temperature=temperature,
                    cause=room_cause,
                    outcome="applied" if applied else "skipped_unavailable",
                )
            if applied:
                self._applied_periods[room.room_id] = key
                applied_any = True
            else:
                _LOGGER.warning(
                    "Scheduled target for ZEAL room %s was not applied; "
                    "waiting for the room thermostat to become available",
                    room.room_id,
                )
        if applied_any:
            await self._coordinator.async_request_refresh()

    def _schedule_next_transition(self, now: datetime) -> None:
        candidates = [
            transition
            for room in self._configuration.rooms.values()
            if (transition := next_transition_after(room, now)) is not None
        ]
        override_expiries = [
            override.expires_at
            for override in self._overrides.values()
            if override.expires_at > now
        ]
        candidates_at = [candidate.starts_at for candidate in candidates]
        candidates_at.extend(override_expiries)
        if not candidates_at:
            return
        next_at = min(candidates_at)
        self._cancel_next = event_helper.async_track_point_in_time(
            self._hass, self._handle_transition, next_at
        )

    @callback
    def _handle_transition(self, now: datetime) -> None:
        self._cancel_next = None
        self._hass.async_create_task(self._async_handle_transition(now))

    async def _async_handle_transition(self, now: datetime) -> None:
        await self._async_apply_active_periods(now, cause="scheduled_transition")
        self._schedule_next_transition(now)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Retry unresolved rooms without repeating already-applied periods."""
        if self._started:
            self._hass.async_create_task(self._async_retry_current_periods())

    async def _async_retry_current_periods(self) -> None:
        await self._async_apply_active_periods(
            dt_util.now(), cause="availability_reconciliation"
        )

    async def async_set_temporary_override(
        self,
        room_ids: list[str],
        *,
        duration: str,
        value: float,
        operation: str,
    ) -> list[TemporaryOverride]:
        """Apply a transient batch target without changing weekly schedules."""
        now = dt_util.now()
        base_temperatures = {
            room_id: override.temperature
            for room_id, override in self._overrides.items()
            if room_id in room_ids and override.expires_at > now
        }
        overrides = create_temporary_overrides(
            self._configuration,
            room_ids,
            now=now,
            duration=duration,
            value=value,
            operation=operation,
            base_temperatures=base_temperatures,
        )
        self._overrides.update(
            {override.room_id: override for override in overrides}
        )
        self._applied_periods.clear()
        self._cancel_pending_transition()
        await self._async_apply_active_periods(
            now, cause="temporary_override_applied"
        )
        self._schedule_next_transition(now)
        return overrides

    async def async_clear_temporary_override(self, room_id: str) -> None:
        """Clear one hold and immediately restore its current schedule."""
        if room_id not in self._configuration.rooms:
            raise ValueError(f"Unknown room: {room_id}")
        self._overrides.pop(room_id, None)
        now = dt_util.now()
        self._applied_periods.clear()
        self._cancel_pending_transition()
        await self._async_apply_active_periods(
            now, cause="temporary_override_cleared"
        )
        self._schedule_next_transition(now)

    def quick_change_state(self) -> dict[str, object]:
        """Return current scheduled/effective targets for the HTML panel."""
        now = dt_util.now()
        rooms: list[dict[str, object]] = []
        for room in self._configuration.rooms.values():
            active = active_period_at(room, now)
            override = self._overrides.get(room.room_id)
            if override is not None and override.expires_at <= now:
                override = None
            transition = next_transition_after(room, now)
            scheduled_temperature = active.period.temperature if active else None
            rooms.append(
                {
                    "room_id": room.room_id,
                    "room_name": room.room_name,
                    "scheduled_temperature": scheduled_temperature,
                    "effective_temperature": (
                        override.temperature if override else scheduled_temperature
                    ),
                    "next_change_at": (
                        transition.starts_at.isoformat() if transition else None
                    ),
                    "override": override.to_dict() if override else None,
                }
            )
        return {"rooms": rooms}
