"""ZEAL-owned scheduling domain.

This package deliberately contains no imports from Visual Climate Scheduler.
The pure model and decision modules also avoid Home Assistant runtime objects.
"""

from .models import (
    SCHEMA_VERSION,
    WEEKDAYS,
    RoomSchedule,
    ScheduleConfiguration,
    SchedulePeriod,
)

__all__ = [
    "SCHEMA_VERSION",
    "WEEKDAYS",
    "RoomSchedule",
    "ScheduleConfiguration",
    "SchedulePeriod",
]
