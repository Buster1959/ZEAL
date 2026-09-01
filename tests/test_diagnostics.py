"""Privacy-boundary tests for ordinary Home Assistant diagnostics."""

from types import SimpleNamespace

from custom_components.zeal.diagnostics import (
    _away_summary,
    _quick_change_summary,
    _schedule_summary,
)
from custom_components.zeal.scheduler.models import RoomSchedule, SchedulePeriod
from custom_components.zeal.scheduler.models import WEEKDAYS


def test_schedule_summary_omits_names_times_and_temperatures():
    room = RoomSchedule(
        "lounge-private-id",
        "Private Lounge Name",
        {
            **{day: () for day in WEEKDAYS},
            "monday": (
                SchedulePeriod("period-1", "Morning", "Morning", "07:00", 20.0),
            ),
        },
    )
    configuration = SimpleNamespace(
        rooms={room.room_id: room}, temperature_unit="°C"
    )

    summary = _schedule_summary(configuration, {room.room_id: "zone_1_room_1"})

    assert summary == {
        "room_count": 1,
        "temperature_unit": "°C",
        "rooms": {
            "zone_1_room_1": {
                "period_count": 1,
                "period_counts_by_day": {
                    "monday": 1,
                    "tuesday": 0,
                    "wednesday": 0,
                    "thursday": 0,
                    "friday": 0,
                    "saturday": 0,
                    "sunday": 0,
                },
            }
        },
    }
    rendered = repr(summary)
    assert "Private Lounge Name" not in rendered
    assert "lounge-private-id" not in rendered
    assert "07:00" not in rendered
    assert "20.0" not in rendered


def test_away_and_quick_change_summaries_omit_private_details():
    away = _away_summary(
        {
            "mode": "date_range",
            "status": "scheduled",
            "active": False,
            "starts_at": "2026-09-10T08:00:00+01:00",
            "ends_at": "2026-09-20T18:00:00+01:00",
            "temperature": 12,
        }
    )
    quick = _quick_change_summary(
        {
            "rooms": [
                {
                    "room_id": "private-room",
                    "effective_temperature": 22,
                    "override": {"expires_at": "private-time"},
                },
                {"room_id": "another-room", "override": None},
            ]
        }
    )

    assert away == {
        "mode": "date_range",
        "status": "scheduled",
        "active": False,
    }
    assert quick == {"room_count": 2, "active_hold_count": 1}
    rendered = repr((away, quick))
    assert "2026-09" not in rendered
    assert "private-room" not in rendered
    assert "22" not in rendered
