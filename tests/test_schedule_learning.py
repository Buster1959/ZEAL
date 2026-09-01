"""Synthetic end-to-end evidence tests for ZEAL Schedule Adaptation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

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


def configuration(*, shared_period_ids: bool = True) -> ScheduleConfiguration:
    days = {}
    for day in WEEKDAYS:
        suffix = "" if shared_period_ids else f"-{day}"
        days[day] = (
            SchedulePeriod(f"morning{suffix}", "morning", "Morning", "07:00", 18),
            SchedulePeriod(f"day{suffix}", "day", "Day", "08:00", 20),
        )
    return ScheduleConfiguration(
        rooms={
            "lounge": RoomSchedule(
                "lounge",
                "Lounge",
                days,
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
    assert change.adaptation_direction == "earlier"
    assert change.period_id == "day"
    assert change.original_time == "08:00"
    assert change.proposed_time == "07:35"


def test_previous_target_just_after_transition_is_later_timing_evidence():
    change = classify_manual_change(configuration(), "lounge", 18, at(3, 8, 20))
    assert change is not None
    assert change.adaptation_type == "timing"
    assert change.adaptation_direction == "later"
    assert change.period_id == "day"
    assert change.original_time == "08:00"
    assert change.proposed_time == "08:20"
    assert change.proposed_temperature == 20


def test_different_target_remains_with_active_adjacent_period():
    change = classify_manual_change(configuration(), "lounge", 19, at(3, 7, 35))
    assert change is not None
    assert change.adaptation_type == "temperature"
    assert change.period_id == "morning"
    assert change.original_time == "07:00"


async def test_three_matching_distinct_days_create_temperature_proposal():
    store = LearningStore(None, "entry", store=MemoryStore())
    engine = ScheduleLearning(
        store, lambda: configuration(shared_period_ids=False), lambda: "revision-one"
    )
    assert await engine.async_record_change(
        room_id="lounge", requested_temperature=19,
        source="home_assistant", when=at(3, 7, 35)
    ) is None
    assert await engine.async_record_change(
        room_id="lounge", requested_temperature=19,
        source="physical_trv", when=at(4, 7, 36)
    ) is None
    proposal = await engine.async_record_change(
        room_id="lounge", requested_temperature=19,
        source="quick_change", when=at(5, 7, 37)
    )
    assert proposal is not None
    assert proposal["weekday"] == "wednesday"
    assert proposal["period_id"] == "morning-wednesday"
    assert proposal["proposed_temperature"] == 19.0
    assert proposal["evidence_count"] == 3


async def test_unrelated_global_revisions_do_not_reset_room_evidence():
    store = LearningStore(None, "entry", store=MemoryStore())
    revision = {"value": "revision-one"}
    engine = ScheduleLearning(store, configuration, lambda: revision["value"])
    proposal = None
    for index, day in enumerate((3, 4, 5), start=1):
        revision["value"] = f"unrelated-global-revision-{index}"
        proposal = await engine.async_record_change(
            room_id="lounge",
            requested_temperature=19,
            source="home_assistant",
            when=at(day, 7, 35),
        )
    assert proposal is not None
    assert proposal["evidence_count"] == 3


async def test_away_change_is_audited_but_excluded_from_detection():
    store = LearningStore(None, "entry", store=MemoryStore())
    engine = ScheduleLearning(
        store,
        configuration,
        lambda: "revision-one",
        exclusion_provider=lambda _room_id: "away_mode_active",
    )
    for day in (3, 4, 5):
        assert await engine.async_record_change(
            room_id="lounge",
            requested_temperature=19,
            source="physical_trv",
            when=at(day, 7, 35),
        ) is None
    assert len(store.events) == 3
    assert {event["outcome"] for event in store.events} == {"excluded"}
    assert {event["excluded_reason"] for event in store.events} == {
        "away_mode_active"
    }
    assert store.proposals == []


async def test_away_events_never_count_toward_a_later_normal_proposal():
    store = LearningStore(None, "entry", store=MemoryStore())
    away = {"active": True}
    engine = ScheduleLearning(
        store,
        configuration,
        lambda: "revision-one",
        exclusion_provider=lambda _room_id: (
            "away_mode_active" if away["active"] else None
        ),
    )
    for day in (3, 4):
        assert await engine.async_record_change(
            room_id="lounge",
            requested_temperature=19,
            source="physical_trv",
            when=at(day, 7, 35),
        ) is None
    away["active"] = False
    assert await engine.async_record_change(
        room_id="lounge",
        requested_temperature=19,
        source="physical_trv",
        when=at(5, 7, 35),
    ) is None
    assert [event["outcome"] for event in store.events] == [
        "excluded",
        "excluded",
        "applied",
    ]
    assert store.proposals == []


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


async def test_learning_store_prunes_events_outside_privacy_retention():
    memory = MemoryStore()
    store = LearningStore(None, "entry", store=memory)
    now = datetime.now(timezone.utc)
    store.events = [
        {"event_id": "expired", "timestamp": (now - timedelta(days=43)).isoformat()},
        {"event_id": "retained", "timestamp": (now - timedelta(days=41)).isoformat()},
    ]
    await store.async_save()
    assert [event["event_id"] for event in store.events] == ["retained"]


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


async def test_earlier_and_later_timing_evidence_never_mix():
    store = LearningStore(None, "entry", store=MemoryStore())
    engine = learning(store)
    for day in (3, 4):
        assert await engine.async_record_change(
            room_id="lounge",
            requested_temperature=20,
            source="home_assistant",
            when=at(day, 7, 40),
        ) is None
    assert await engine.async_record_change(
        room_id="lounge",
        requested_temperature=18,
        source="home_assistant",
        when=at(5, 8, 20),
    ) is None
    assert store.proposals == []
