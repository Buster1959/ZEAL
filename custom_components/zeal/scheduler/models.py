"""Versioned, JSON-serialisable ZEAL schedule models.

Schedules bind only to stable ZEAL room IDs. Physical TRV entity IDs are not
part of this contract and can never become independent scheduler targets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import re
from typing import Any, Iterable, Mapping

from ..const import MAX_TARGET_TEMPERATURE, MIN_TARGET_TEMPERATURE

SCHEMA_VERSION = 1
WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
TEMPERATURE_UNITS = ("°C", "°F")

_TIME_PATTERN = re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _json_object_copy(value: Mapping[str, Any], field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    try:
        copied = json.loads(json.dumps(dict(value), allow_nan=False))
    except (TypeError, ValueError) as err:
        raise ValueError(f"{field_name} must contain JSON-serialisable data") from err
    if not isinstance(copied, dict):
        raise ValueError(f"{field_name} must be an object")
    return copied


def validate_time(value: Any) -> str:
    value = _require_string(value, "time")
    if not _TIME_PATTERN.fullmatch(value):
        raise ValueError("time must use an exact 24-hour HH:MM format")
    return value


def validate_temperature_unit(value: Any) -> str:
    if value not in TEMPERATURE_UNITS:
        raise ValueError("temperature_unit must be °C or °F")
    return value


@dataclass(frozen=True, slots=True)
class SchedulePeriod:
    """One named target-temperature change within a day."""

    id: str
    friendly_name: str
    name: str
    time: str
    temperature: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_string(self.id, "period.id"))
        object.__setattr__(
            self,
            "friendly_name",
            _require_string(self.friendly_name, "period.friendly_name"),
        )
        object.__setattr__(self, "name", _require_string(self.name, "period.name"))
        object.__setattr__(self, "time", validate_time(self.time))
        if isinstance(self.temperature, bool) or not isinstance(
            self.temperature, (int, float)
        ):
            raise ValueError("period.temperature must be a number")
        temperature = float(self.temperature)
        if not math.isfinite(temperature):
            raise ValueError("period.temperature must be finite")
        if not MIN_TARGET_TEMPERATURE <= temperature <= MAX_TARGET_TEMPERATURE:
            raise ValueError(
                "period.temperature must be between "
                f"{MIN_TARGET_TEMPERATURE} and {MAX_TARGET_TEMPERATURE}°C"
            )
        object.__setattr__(self, "temperature", temperature)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SchedulePeriod":
        if not isinstance(value, Mapping):
            raise ValueError("schedule period must be an object")
        return cls(
            id=value.get("id"),
            friendly_name=value.get("friendly_name"),
            name=value.get("name"),
            time=value.get("time"),
            temperature=value.get("temperature"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "friendly_name": self.friendly_name,
            "name": self.name,
            "time": self.time,
            "temperature": self.temperature,
        }


def validate_periods(
    day: str, periods: Iterable[SchedulePeriod]
) -> tuple[SchedulePeriod, ...]:
    if day not in WEEKDAYS:
        raise ValueError(f"unknown weekday: {day}")
    normalized = tuple(periods)
    if any(not isinstance(period, SchedulePeriod) for period in normalized):
        raise ValueError(f"room.days.{day} must contain schedule periods")
    if len({period.id for period in normalized}) != len(normalized):
        raise ValueError(f"room.days.{day} contains duplicate period ids")
    if len({period.time for period in normalized}) != len(normalized):
        raise ValueError(f"room.days.{day} contains duplicate period times")
    if tuple(period.time for period in normalized) != tuple(
        sorted(period.time for period in normalized)
    ):
        raise ValueError(f"room.days.{day} must be ordered by time")
    return normalized


def copy_periods(periods: Iterable[SchedulePeriod]) -> tuple[SchedulePeriod, ...]:
    return tuple(SchedulePeriod.from_dict(period.to_dict()) for period in periods)


@dataclass(frozen=True, slots=True)
class RoomSchedule:
    """Seven-day schedule for one stable ZEAL room ID."""

    room_id: str
    room_name: str
    days: Mapping[str, Iterable[SchedulePeriod]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "room_id", _require_string(self.room_id, "room.room_id"))
        object.__setattr__(
            self, "room_name", _require_string(self.room_name, "room.room_name")
        )
        if set(self.days) != set(WEEKDAYS):
            raise ValueError("room.days must contain exactly monday through sunday")
        object.__setattr__(
            self,
            "days",
            {day: validate_periods(day, self.days[day]) for day in WEEKDAYS},
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RoomSchedule":
        if not isinstance(value, Mapping):
            raise ValueError("room must be an object")
        raw_days = value.get("days")
        if not isinstance(raw_days, Mapping):
            raise ValueError("room.days must be an object")
        days: dict[str, tuple[SchedulePeriod, ...]] = {}
        for day, raw_periods in raw_days.items():
            if not isinstance(raw_periods, list):
                raise ValueError(f"room.days.{day} must be a list")
            days[day] = tuple(SchedulePeriod.from_dict(period) for period in raw_periods)
        return cls(
            room_id=value.get("room_id"),
            room_name=value.get("room_name"),
            days=days,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "days": {
                day: [period.to_dict() for period in self.days[day]]
                for day in WEEKDAYS
            },
        }


@dataclass(frozen=True, slots=True)
class ScheduleConfiguration:
    """Complete scheduler document for one ZEAL config entry."""

    version: int = SCHEMA_VERSION
    rooms: Mapping[str, RoomSchedule] = field(default_factory=dict)
    settings: Mapping[str, Any] = field(default_factory=dict)
    temperature_unit: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.version, bool) or self.version != SCHEMA_VERSION:
            raise ValueError(f"unsupported schedule configuration version: {self.version}")
        rooms = dict(self.rooms)
        if any(not isinstance(room, RoomSchedule) for room in rooms.values()):
            raise ValueError("configuration.rooms must contain room schedules")
        if any(room_id != room.room_id for room_id, room in rooms.items()):
            raise ValueError("configuration room keys must match room.room_id")
        object.__setattr__(self, "rooms", rooms)
        object.__setattr__(
            self, "settings", _json_object_copy(self.settings, "configuration.settings")
        )
        if self.temperature_unit is not None:
            object.__setattr__(
                self,
                "temperature_unit",
                validate_temperature_unit(self.temperature_unit),
            )

    @classmethod
    def empty(cls) -> "ScheduleConfiguration":
        return cls()

    def with_temperature_unit(self, unit: str) -> "ScheduleConfiguration":
        return ScheduleConfiguration(
            rooms=self.rooms,
            settings=self.settings,
            temperature_unit=validate_temperature_unit(unit),
        )

    @staticmethod
    def migrate_dict(value: Mapping[str, Any]) -> dict[str, Any]:
        """Migrate the pre-versioned ZEAL prototype shape to schema V1."""
        migrated = _json_object_copy(value, "schedule configuration")
        version = migrated.get("version", 0)
        if isinstance(version, bool) or not isinstance(version, int):
            raise ValueError("schedule configuration version must be an integer")
        if version == 0:
            migrated["version"] = 1
            migrated.setdefault("temperature_unit", None)
            version = 1
        if version != SCHEMA_VERSION:
            raise ValueError(f"unsupported schedule configuration version: {version}")
        return migrated

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScheduleConfiguration":
        value = cls.migrate_dict(value)
        raw_rooms = value.get("rooms", {})
        raw_settings = value.get("settings", {})
        if not isinstance(raw_rooms, Mapping):
            raise ValueError("configuration.rooms must be an object")
        if not isinstance(raw_settings, Mapping):
            raise ValueError("configuration.settings must be an object")
        return cls(
            version=value["version"],
            rooms={
                room_id: RoomSchedule.from_dict(room)
                for room_id, room in raw_rooms.items()
            },
            settings=raw_settings,
            temperature_unit=value.get("temperature_unit"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "rooms": {
                room_id: room.to_dict() for room_id, room in self.rooms.items()
            },
            "settings": _json_object_copy(self.settings, "configuration.settings"),
            "temperature_unit": self.temperature_unit,
        }
