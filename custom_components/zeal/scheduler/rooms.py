"""Synchronise schedule records with ZEAL's stable room registry."""

from __future__ import annotations

from collections.abc import Mapping

from .models import RoomSchedule, ScheduleConfiguration, WEEKDAYS


def reconcile_room_schedules(
    configuration: ScheduleConfiguration,
    configured_rooms: Mapping[str, str],
) -> ScheduleConfiguration:
    """Match schedules to current ``room_id -> display name`` configuration.

    Existing daily schedules survive name changes. New rooms receive empty days;
    removed room IDs are removed from the scheduler document.
    """
    rooms: dict[str, RoomSchedule] = {}
    for room_id, room_name in configured_rooms.items():
        existing = configuration.rooms.get(room_id)
        rooms[room_id] = RoomSchedule(
            room_id=room_id,
            room_name=room_name,
            days=(
                existing.days
                if existing is not None
                else {day: () for day in WEEKDAYS}
            ),
        )
    return ScheduleConfiguration(
        rooms=rooms,
        settings=configuration.settings,
        temperature_unit=configuration.temperature_unit,
    )
