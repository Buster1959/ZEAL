"""Deterministic schedule selection without Home Assistant runtime objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .models import RoomSchedule, SchedulePeriod, WEEKDAYS


@dataclass(frozen=True, slots=True)
class ScheduledPeriod:
    """A period paired with the local date on which it starts."""

    day: str
    starts_at: datetime
    period: SchedulePeriod


def _weekday(value: date) -> str:
    return WEEKDAYS[value.weekday()]


def _starts_at(value: date, period: SchedulePeriod, reference: datetime) -> datetime:
    return datetime.combine(value, time.fromisoformat(period.time), tzinfo=reference.tzinfo)


def active_period_at(room: RoomSchedule, when: datetime) -> ScheduledPeriod | None:
    """Return the latest active period, carrying across midnight/empty days."""
    for offset in range(len(WEEKDAYS)):
        candidate_date = when.date() - timedelta(days=offset)
        day = _weekday(candidate_date)
        periods = room.days[day]
        if not periods:
            continue
        if offset == 0:
            eligible = [
                period
                for period in periods
                if _starts_at(candidate_date, period, when) <= when
            ]
            if not eligible:
                continue
            period = eligible[-1]
        else:
            period = periods[-1]
        return ScheduledPeriod(day, _starts_at(candidate_date, period, when), period)
    return None


def next_transition_after(room: RoomSchedule, when: datetime) -> ScheduledPeriod | None:
    """Return the first strictly future target change within one week."""
    for offset in range(len(WEEKDAYS) + 1):
        candidate_date = when.date() + timedelta(days=offset)
        day = _weekday(candidate_date)
        for period in room.days[day]:
            starts_at = _starts_at(candidate_date, period, when)
            if starts_at > when:
                return ScheduledPeriod(day, starts_at, period)
    return None
