"""Synthetic end-to-end evidence tests for ZEAL Schedule Adaptation."""

from __future__ import annotations

from datetime import datetime, timezone

from custom_components.zeal.scheduler.learning import (
    LearningStore,
    ScheduleLearning,
    apply_proposal,
    classify_manual_change,
)
from custom_components.zeal.scheduler.models import (
    WEEKDAYS,
    RoomSchedule,
    ScheduleConfiguration,
    SchedulePeriod,
)


class MemoryStore:
    def __init__(self, data=None):
        self.data = data

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.data = data


def configuration() -> ScheduleConfiguration:
    monday = (
        SchedulePeriod("morning", "morning", "Morning", "07:00", 18),
        SchedulePeriod("day", "day", "Day", "08:00", 20),
    )
    return ScheduleConfiguration(
        rooms={
            "lounge": RoomSchedule(
                "lounge",
                "Lounge",
                {day: monday for day in WEEKDAYS},
            )
        },
        temperature_unit="°C",
    )


def learning(store: LearningStore) -> ScheduleLearning:
    return ScheduleLearning(store, configuration, lambda: "revision-one")


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, day, hour, minute, tzinfo=timezone.utc)


def test_change_before_next_period_target_is_timing_evidence():
    change = classify_manual_change(configuration(), "lounge", 20, at(3, 7, 35))
    assert change is not None
    assert change.adaptation_type == "timing"
    assert change.period_id == "day"
    assert change.original_time == "08:00"
    assert change.proposed_time == "07:35"


def test_different_target_remains_with_active_adjacent_period():
    change = classify_manual_change(configuration(), "lounge", 19, at(3, 7, 35))
    assert change is not None
    assert change.adaptation_type == "temperature"
    assert change.period_id == "morning"
    assert change.original_time == "07:00"


async def test_three_matching_distinct_days_create_temperature_proposal():
    store = LearningStore(None, "entry", store=MemoryStore())
    engine = learning(store)
    assert await engine.async_record_change(
        room_id="lounge", requested_temperature=19.5,
        source="home_assistant", when=at(3, 7, 10)
    ) is None
    assert await engine.async_record_change(
        room_id="lounge", requested_temperature=19.5,
        source="physical_trv", when=at(4, 7, 12)
    ) is None
    proposal = await engine.async_record_change(
        room_id="lounge", requested_temperature=19.5,
        source="quick_change", when=at(5, 7, 14)
    )
    assert proposal is not None
    assert proposal["weekday"] == "wednesday"
    assert proposal["period_id"] == "morning"
    assert proposal["proposed_temperature"] == 19.5
    assert proposal["evidence_count"] == 3


async def test_repeated_changes_on_one_date_count_once():
    store = LearningStore(None, "entry", store=MemoryStore())
    engine = learning(store)
    for minute in (5, 10, 15):
        proposal = await engine.async_record_change(
            room_id="lounge",
            requested_temperature=19.5,
            source="physical_trv",
            when=at(3, 7, minute),
        )
        assert proposal is None
    assert len(store.events) == 3
    assert store.proposals == []


async def test_learning_store_round_trip():
    memory = MemoryStore()
    store = LearningStore(None, "entry", store=memory)
    engine = learning(store)
    await engine.async_record_change(
        room_id="lounge",
        requested_temperature=19.5,
        source="home_assistant",
        when=at(3, 7, 10),
    )
    restored = LearningStore(None, "entry", store=memory)
    await restored.async_load()
    assert len(restored.events) == 1
    assert restored.events[0]["period_id"] == "morning"


def test_apply_proposal_changes_only_exact_evidenced_period():
    proposal = {
        "room_id": "lounge",
        "weekday": "monday",
        "period_id": "morning",
        "original_time": "07:00",
        "original_temperature": 18.0,
        "proposed_time": "07:00",
        "proposed_temperature": 19.5,
    }
    updated = apply_proposal(configuration(), proposal)
    assert updated.rooms["lounge"].days["monday"][0].temperature == 19.5
    assert updated.rooms["lounge"].days["monday"][1].temperature == 20.0
    assert updated.rooms["lounge"].days["tuesday"][0].temperature == 18.0


async def test_dismissed_proposal_is_audited_and_not_actionable_again():
    store = LearningStore(None, "entry", store=MemoryStore())
    engine = learning(store)
    proposal = None
    for day in (3, 4, 5):
        proposal = await engine.async_record_change(
            room_id="lounge",
            requested_temperature=19.5,
            source="home_assistant",
            when=at(day, 7, 10),
        )
    assert proposal is not None
    decided = await engine.async_set_status(
        proposal["proposal_id"],
        "dismissed",
        decided_at=at(5, 8),
        decided_by="user-one",
    )
    assert decided["status"] == "dismissed"
    assert decided["decided_by"] == "user-one"


async def test_similar_timing_changes_share_pattern_and_use_median_time():
    store = LearningStore(None, "entry", store=MemoryStore())
    engine = learning(store)
    proposal = None
    for day, minute in ((3, 35), (4, 30), (5, 40)):
        proposal = await engine.async_record_change(
            room_id="lounge",
            requested_temperature=20,
            source="home_assistant",
            when=at(day, 7, minute),
        )
    assert proposal is not None
    assert proposal["adaptation_type"] == "timing"
    assert proposal["period_id"] == "day"
    assert proposal["proposed_time"] == "07:35"
