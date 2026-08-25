"""Validated immutable updates used by ZEAL's future HTML editor."""

from __future__ import annotations

from typing import Any, Mapping

from .models import RoomSchedule, ScheduleConfiguration, copy_periods


def update_room_days(
    configuration: ScheduleConfiguration,
    room_id: str,
    days: Mapping[str, Any],
) -> ScheduleConfiguration:
    room = configuration.rooms.get(room_id)
    if room is None:
        raise KeyError(room_id)
    raw_room = room.to_dict()
    raw_room["days"] = days
    updated = RoomSchedule.from_dict(raw_room)
    return ScheduleConfiguration(
        rooms={**configuration.rooms, room_id: updated},
        settings=configuration.settings,
        temperature_unit=configuration.temperature_unit,
    )


def copy_room_schedule(
    configuration: ScheduleConfiguration,
    source_room_id: str,
    target_room_ids: list[str],
    source_days: Mapping[str, Any],
) -> ScheduleConfiguration:
    """Save the source editor state, then copy only its seven daily lists."""
    if not target_room_ids or len(set(target_room_ids)) != len(target_room_ids):
        raise ValueError("Select one or more different destination rooms")
    if source_room_id in target_room_ids:
        raise ValueError("A room cannot be copied to itself")
    updated = update_room_days(configuration, source_room_id, source_days)
    unknown = [room_id for room_id in target_room_ids if room_id not in updated.rooms]
    if unknown:
        raise KeyError(unknown[0])
    source = updated.rooms[source_room_id]
    rooms = dict(updated.rooms)
    for room_id in target_room_ids:
        target = rooms[room_id]
        rooms[room_id] = RoomSchedule(
            room_id=target.room_id,
            room_name=target.room_name,
            days={day: copy_periods(source.days[day]) for day in source.days},
        )
    return ScheduleConfiguration(
        rooms=rooms,
        settings=updated.settings,
        temperature_unit=updated.temperature_unit,
    )
