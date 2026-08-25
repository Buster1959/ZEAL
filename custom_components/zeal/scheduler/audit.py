"""Bounded persistent audit trail for ZEAL scheduler applications."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ..const import (
    AUDIT_MAX_ENTRIES,
    AUDIT_STORAGE_KEY_FMT,
    AUDIT_STORAGE_VERSION,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class AuditLog:
    """Persist recent canonical room-target outcomes without secrets."""

    def __init__(
        self, hass: HomeAssistant, entry_id: str, store: Any | None = None
    ) -> None:
        if store is None:
            from homeassistant.helpers.storage import Store

            store = Store[dict[str, object]](
                hass,
                AUDIT_STORAGE_VERSION,
                AUDIT_STORAGE_KEY_FMT.format(entry_id=entry_id),
            )
        self._store = store
        self._entries: list[dict[str, object]] = []

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if not isinstance(data, dict) or data.get("version") != AUDIT_STORAGE_VERSION:
            self._entries = []
            return
        entries = data.get("entries")
        self._entries = (
            [dict(entry) for entry in entries if isinstance(entry, dict)][
                -AUDIT_MAX_ENTRIES:
            ]
            if isinstance(entries, list)
            else []
        )

    async def async_record(
        self,
        *,
        timestamp: datetime,
        room_id: str,
        room_name: str,
        canonical_entity_id: str | None,
        previous_temperature: float | None,
        requested_temperature: float,
        cause: str,
        outcome: str,
    ) -> None:
        self._entries.append(
            {
                "timestamp": timestamp.isoformat(),
                "room_id": room_id,
                "room_name": room_name,
                "canonical_entity_id": canonical_entity_id,
                "previous_temperature": previous_temperature,
                "requested_temperature": float(requested_temperature),
                "cause": cause,
                "outcome": outcome,
            }
        )
        self._entries = self._entries[-AUDIT_MAX_ENTRIES:]
        await self._store.async_save(
            {"version": AUDIT_STORAGE_VERSION, "entries": self._entries}
        )

    def export(self) -> dict[str, object]:
        return {
            "version": AUDIT_STORAGE_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "maximum_entries": AUDIT_MAX_ENTRIES,
            "entries": [dict(entry) for entry in self._entries],
        }
