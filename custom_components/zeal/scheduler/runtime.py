"""Home Assistant adapter for ZEAL's deterministic schedule engine."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import event as event_helper
from homeassistant.util import dt as dt_util

from ..coordinator import ZealCoordinator
from .engine import active_period_at, next_transition_after
from .models import ScheduleConfiguration

_LOGGER = logging.getLogger(__name__)


class ScheduleRuntime:
    """Apply room schedules only through ZEAL's canonical setpoint boundary."""

    def __init__(self, hass: HomeAssistant, coordinator: ZealCoordinator) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._configuration = ScheduleConfiguration.empty()
        self._cancel_next: Callable[[], None] | None = None
        self._unsub_coordinator: Callable[[], None] | None = None
        self._applied_periods: dict[str, tuple[datetime, str]] = {}
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

    async def async_set_configuration(
        self,
        configuration: ScheduleConfiguration,
        *,
        cause: str = "configuration_saved",
    ) -> None:
        """Replace the document, apply current periods and reset the timer."""
        self._configuration = configuration
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
            if active is None:
                continue
            key = (active.starts_at, active.period.id)
            if self._applied_periods.get(room.room_id) == key:
                continue
            applied = await self._coordinator.async_set_room_target(
                room.room_id,
                active.period.temperature,
                source=cause,
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
        if not candidates:
            return
        next_at = min(candidate.starts_at for candidate in candidates)
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
