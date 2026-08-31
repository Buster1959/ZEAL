"""Home Assistant adapter for ZEAL's deterministic schedule engine."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import event as event_helper
from homeassistant.util import dt as dt_util

from ..const import ROOM_ACTIVE, ROOM_ID, ZONE_ROOMS
from ..coordinator import ZealCoordinator
from .away import AwayModeConfiguration
from .audit import AuditLog
from .engine import active_period_at, next_transition_after
from .models import ScheduleConfiguration
from .overrides import TemporaryOverride, create_temporary_overrides

if TYPE_CHECKING:
    from .learning import ScheduleLearning

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
        self.learning: ScheduleLearning | None = None
        self._configuration = ScheduleConfiguration.empty()
        self._cancel_next: Callable[[], None] | None = None
        self._unsub_coordinator: Callable[[], None] | None = None
        self._unsub_away_calendar: Callable[[], None] | None = None
        self._tracked_away_calendar: str | None = None
        self._away_mode = AwayModeConfiguration()
        self._away_was_active = False
        self._applied_periods: dict[str, tuple[object, str]] = {}
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
        self._remove_away_calendar_listener()
        self._applied_periods.clear()
        self._overrides.clear()

    async def async_set_configuration(
        self,
        configuration: ScheduleConfiguration,
        *,
        cause: str = "configuration_saved",
    ) -> None:
        """Replace the document, apply current periods and reset the timer."""
        away_mode = AwayModeConfiguration.from_settings(configuration.settings)
        self._configuration = configuration
        self._away_mode = away_mode
        self._sync_away_calendar_listener()
        self._overrides = {
            room_id: override
            for room_id, override in self._overrides.items()
            if room_id in configuration.rooms
        }
        self._applied_periods.clear()
        self._cancel_pending_transition()
        now = dt_util.now()
        self._away_was_active = self._away_active(now)
        await self._async_apply_active_periods(now, cause=cause)
        self._schedule_next_transition(now)

    def _remove_away_calendar_listener(self) -> None:
        if self._unsub_away_calendar is not None:
            self._unsub_away_calendar()
            self._unsub_away_calendar = None
        self._tracked_away_calendar = None

    def _sync_away_calendar_listener(self) -> None:
        calendar_entity_id = (
            self._away_mode.calendar_entity_id
            if self._away_mode.mode == "calendar"
            else None
        )
        if calendar_entity_id == self._tracked_away_calendar:
            return
        self._remove_away_calendar_listener()
        if calendar_entity_id is None or not self._started:
            return
        self._unsub_away_calendar = event_helper.async_track_state_change_event(
            self._hass,
            [calendar_entity_id],
            self._handle_away_calendar_change,
        )
        self._tracked_away_calendar = calendar_entity_id

    def _calendar_is_on(self) -> bool:
        entity_id = self._away_mode.calendar_entity_id
        state = self._hass.states.get(entity_id) if entity_id else None
        return state is not None and state.state == "on"

    def _away_active(self, now: datetime) -> bool:
        return self._away_mode.active_at(
            now,
            calendar_is_on=(
                self._calendar_is_on() if self._away_mode.mode == "calendar" else False
            ),
        )

    def _away_room_ids(self) -> set[str]:
        zones = getattr(self._coordinator, "zones", None)
        if zones is None:
            return set(self._configuration.rooms)
        return {
            room[ROOM_ID]
            for zone in zones
            for room in zone.get(ZONE_ROOMS, [])
            if room.get(ROOM_ACTIVE, True)
            and room.get(ROOM_ID) in self._configuration.rooms
        }

    @callback
    def _handle_away_calendar_change(self, event) -> None:
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        was_active = old_state is not None and old_state.state == "on"
        is_active = new_state is not None and new_state.state == "on"
        if was_active == is_active:
            return
        self._hass.async_create_task(
            self._async_handle_away_transition(is_active, dt_util.now())
        )

    async def _async_handle_away_transition(
        self, is_active: bool, now: datetime
    ) -> None:
        self._away_was_active = is_active
        self._applied_periods.clear()
        self._cancel_pending_transition()
        await self._async_apply_active_periods(
            now,
            cause="away_mode_activated" if is_active else "away_mode_ended",
        )
        self._schedule_next_transition(now)

    def _cancel_pending_transition(self) -> None:
        if self._cancel_next is not None:
            self._cancel_next()
            self._cancel_next = None

    async def _async_apply_active_periods(
        self, now: datetime, *, cause: str
    ) -> None:
        applied_any = False
        away_is_active = self._away_active(now)
        away_room_ids = self._away_room_ids() if away_is_active else set()
        for room in self._configuration.rooms.values():
            active = active_period_at(room, now)
            override = self._overrides.get(room.room_id)
            override_expired = False
            if override is not None and override.expires_at <= now:
                self._overrides.pop(room.room_id, None)
                override = None
                override_expired = True
            away_applies = away_is_active and room.room_id in away_room_ids
            if not away_applies and active is None and override is None:
                continue
            if away_applies:
                key = (
                    "away",
                    f"{self._away_mode.mode}:{self._away_mode.temperature}",
                )
                temperature = self._away_mode.temperature
                room_cause = (
                    cause if cause.startswith("away_mode_") else "away_mode_active"
                )
                effective_source = "away"
            elif override is not None:
                key = (override.expires_at, f"override:{override.temperature}")
                temperature = override.temperature
                room_cause = (
                    "temporary_override_resumed_after_away"
                    if cause == "away_mode_ended"
                    else cause
                )
                effective_source = "temporary_override"
            else:
                key = (active.starts_at, active.period.id)
                temperature = active.period.temperature
                room_cause = (
                    "temporary_override_expired" if override_expired else cause
                )
                effective_source = "schedule"
            thermostat = getattr(self._coordinator, "room_thermostats", {}).get(
                room.room_id
            )
            previous = getattr(thermostat, "target_temperature", None)
            previous_temperature = (
                float(previous)
                if isinstance(previous, (int, float)) and not isinstance(previous, bool)
                else None
            )
            if self._applied_periods.get(room.room_id) == key:
                if effective_source == "schedule" or thermostat is None:
                    continue
                if (
                    previous_temperature is not None
                    and abs(previous_temperature - temperature) < 0.01
                ):
                    continue
                room_cause = f"{effective_source}_reasserted"
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
        away_boundary = self._away_mode.next_boundary_after(now)
        if away_boundary is not None:
            candidates_at.append(away_boundary)
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
        away_is_active = self._away_active(now)
        away_changed = away_is_active != self._away_was_active
        if away_changed:
            self._applied_periods.clear()
        self._away_was_active = away_is_active
        await self._async_apply_active_periods(
            now,
            cause=(
                "away_mode_activated"
                if away_is_active and away_changed
                else "away_mode_ended"
                if away_changed
                else "scheduled_transition"
            ),
        )
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
        if self._away_active(now):
            raise ValueError(
                "Quick Change is unavailable while global Away mode is active"
            )
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
        if self.learning is not None:
            for override in overrides:
                await self.learning.async_record_change(
                    room_id=override.room_id,
                    requested_temperature=override.temperature,
                    source="quick_change",
                    when=now,
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
        away_state = self.away_mode_state(now)
        away_room_ids = self._away_room_ids() if away_state["active"] else set()
        rooms: list[dict[str, object]] = []
        for room in self._configuration.rooms.values():
            active = active_period_at(room, now)
            override = self._overrides.get(room.room_id)
            if override is not None and override.expires_at <= now:
                override = None
            transition = next_transition_after(room, now)
            scheduled_temperature = active.period.temperature if active else None
            away_applies = room.room_id in away_room_ids
            effective_source = (
                "away"
                if away_applies
                else "temporary_override"
                if override
                else "schedule"
                if scheduled_temperature is not None
                else None
            )
            rooms.append(
                {
                    "room_id": room.room_id,
                    "room_name": room.room_name,
                    "scheduled_temperature": scheduled_temperature,
                    "scheduled_period_started_at": (
                        active.starts_at.isoformat() if active else None
                    ),
                    "effective_temperature": (
                        self._away_mode.temperature
                        if away_applies
                        else override.temperature
                        if override
                        else scheduled_temperature
                    ),
                    "effective_source": effective_source,
                    "next_change_at": (
                        transition.starts_at.isoformat() if transition else None
                    ),
                    "override": override.to_dict() if override else None,
                }
            )
        return {"away_mode": away_state, "rooms": rooms}

    def away_mode_state(self, now: datetime | None = None) -> dict[str, object]:
        """Return persisted Away settings plus current source status."""
        now = now or dt_util.now()
        active = self._away_active(now)
        if self._away_mode.mode == "off":
            status = "off"
        elif self._away_mode.mode == "calendar":
            state = self._hass.states.get(self._away_mode.calendar_entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                status = "calendar_unavailable"
            else:
                status = "active" if active else "waiting"
        elif active:
            status = "active"
        elif now < self._away_mode.start_datetime:
            status = "scheduled"
        else:
            status = "finished"
        return {
            **self._away_mode.to_dict(),
            "active": active,
            "status": status,
            "active_room_ids": sorted(self._away_room_ids()) if active else [],
        }
