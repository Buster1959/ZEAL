"""Validated global calendar/date-range Away-mode settings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any, Literal, Mapping

from ..const import MAX_TARGET_TEMPERATURE, MIN_TARGET_TEMPERATURE
from .models import ScheduleConfiguration

AWAY_MODE_SETTINGS_KEY = "away_mode"
DEFAULT_AWAY_TEMPERATURE = 12.0
AwayMode = Literal["off", "calendar", "date_range"]


def _parse_timestamp(value: Any, field: str) -> datetime | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as err:
        raise ValueError(f"{field} must be a valid ISO timestamp") from err
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


@dataclass(frozen=True, slots=True)
class AwayModeConfiguration:
    """One mutually-exclusive activation source and global active-room target."""

    mode: AwayMode = "off"
    calendar_entity_id: str | None = None
    starts_at: str | None = None
    ends_at: str | None = None
    temperature: float = DEFAULT_AWAY_TEMPERATURE

    def __post_init__(self) -> None:
        if self.mode not in ("off", "calendar", "date_range"):
            raise ValueError("Away mode must be off, calendar or date_range")
        entity_id = self.calendar_entity_id
        if entity_id is not None:
            if not isinstance(entity_id, str) or not entity_id:
                raise ValueError("Away calendar must be an entity ID or null")
            if not entity_id.startswith("calendar."):
                raise ValueError("Away calendar must be a calendar entity")
        starts_at = _parse_timestamp(self.starts_at, "Away start")
        ends_at = _parse_timestamp(self.ends_at, "Away end")
        if (starts_at is None) != (ends_at is None):
            raise ValueError("Away start and end must both be provided")
        if starts_at is not None and ends_at <= starts_at:
            raise ValueError("Away end must be later than Away start")
        if self.mode == "calendar" and entity_id is None:
            raise ValueError("Choose a Home Assistant calendar for Away mode")
        if self.mode == "date_range" and starts_at is None:
            raise ValueError("Choose an Away start and end date/time")
        temperature = self.temperature
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not math.isfinite(temperature)
        ):
            raise ValueError("Away temperature must be a finite number")
        temperature = float(temperature)
        if not MIN_TARGET_TEMPERATURE <= temperature <= MAX_TARGET_TEMPERATURE:
            raise ValueError(
                "Away temperature must be between "
                f"{MIN_TARGET_TEMPERATURE} and {MAX_TARGET_TEMPERATURE}°C"
            )
        object.__setattr__(self, "temperature", temperature)

    @property
    def enabled(self) -> bool:
        return self.mode != "off"

    @property
    def start_datetime(self) -> datetime | None:
        return _parse_timestamp(self.starts_at, "Away start")

    @property
    def end_datetime(self) -> datetime | None:
        return _parse_timestamp(self.ends_at, "Away end")

    def active_at(self, now: datetime, *, calendar_is_on: bool = False) -> bool:
        if self.mode == "calendar":
            return calendar_is_on
        if self.mode != "date_range":
            return False
        return self.start_datetime <= now < self.end_datetime

    def next_boundary_after(self, now: datetime) -> datetime | None:
        if self.mode != "date_range":
            return None
        if now < self.start_datetime:
            return self.start_datetime
        if now < self.end_datetime:
            return self.end_datetime
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "calendar_entity_id": self.calendar_entity_id,
            "starts_at": self.starts_at,
            "ends_at": self.ends_at,
            "temperature": self.temperature,
        }

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> "AwayModeConfiguration":
        raw = settings.get(AWAY_MODE_SETTINGS_KEY)
        if raw is None:
            return cls()
        if not isinstance(raw, Mapping):
            raise ValueError("schedule.settings.away_mode must be an object")
        calendar_entity_id = raw.get("calendar_entity_id") or None
        return cls(
            mode=raw.get("mode") or ("calendar" if calendar_entity_id else "off"),
            calendar_entity_id=calendar_entity_id,
            starts_at=raw.get("starts_at") or None,
            ends_at=raw.get("ends_at") or None,
            temperature=raw.get("temperature", DEFAULT_AWAY_TEMPERATURE),
        )


def with_away_mode(
    configuration: ScheduleConfiguration, away_mode: AwayModeConfiguration
) -> ScheduleConfiguration:
    """Return the schedule document with only Away settings replaced."""
    settings = dict(configuration.settings)
    settings[AWAY_MODE_SETTINGS_KEY] = away_mode.to_dict()
    return ScheduleConfiguration(
        rooms=configuration.rooms,
        settings=settings,
        temperature_unit=configuration.temperature_unit,
    )
