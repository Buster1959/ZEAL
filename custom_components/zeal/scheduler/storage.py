"""Separate Home Assistant Store adapter for ZEAL schedule configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..const import SCHEDULE_STORAGE_KEY_FMT, SCHEDULE_STORAGE_VERSION
from .models import ScheduleConfiguration

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class ScheduleStorage:
    """Persist schedules independently from Coordinator runtime state."""

    def __init__(
        self, hass: HomeAssistant, entry_id: str, store: Any | None = None
    ) -> None:
        if store is None:
            from homeassistant.helpers.storage import Store

            store = Store[dict[str, object]](
                hass,
                SCHEDULE_STORAGE_VERSION,
                SCHEDULE_STORAGE_KEY_FMT.format(entry_id=entry_id),
            )
        self._store = store

    async def async_load(self) -> ScheduleConfiguration:
        data = await self._store.async_load()
        if data is None:
            return ScheduleConfiguration.empty()
        return ScheduleConfiguration.from_dict(data)

    async def async_save(self, configuration: ScheduleConfiguration) -> None:
        await self._store.async_save(configuration.to_dict())
