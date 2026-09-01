"""Tests for the Room Thermal Response persistence foundation."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from custom_components.zeal.const import (
    THERMAL_CHECKPOINT_INTERVAL_SECONDS,
    THERMAL_MAX_EPISODES_PER_ROOM,
    THERMAL_MAX_SAMPLES_PER_ROOM,
)
from custom_components.zeal.thermal_storage import (
    ThermalStorage,
    ThermalStorageVersionError,
)


class MemoryStore:
    """Small Store test double with observable delayed/final writes."""

    def __init__(self) -> None:
        self.data = None
        self.delayed = None
        self.delay = None
        self.removed = False
        self.save_count = 0

    async def async_load(self):
        return deepcopy(self.data)

    async def async_save(self, data):
        self.data = deepcopy(data)
        self.save_count += 1
        self.removed = False

    def async_delay_save(self, data_func, delay):
        self.delayed = data_func
        self.delay = delay

    async def flush_final_write(self):
        if self.delayed is not None:
            data_func = self.delayed
            self.delayed = None
            await self.async_save(data_func())

    async def async_remove(self):
        self.data = None
        self.removed = True


class StoreFactory:
    def __init__(self) -> None:
        self.stores = {}

    def __call__(self, _version, key, _serialize_in_event_loop):
        return self.stores.setdefault(key, MemoryStore())


@pytest.fixture
def now():
    return datetime(2026, 9, 1, 12, tzinfo=timezone.utc)


@pytest.fixture
def factory():
    return StoreFactory()


@pytest.fixture
def storage(factory, now):
    return ThermalStorage(None, "entry", store_factory=factory, now=lambda: now)


def sample(record_id, timestamp):
    return {
        "id": record_id,
        "timestamp": timestamp.isoformat(),
        "room_temperature": 18.5,
        "outside_temperature": 5.0,
        "effective_target": 21.0,
        "demand": True,
        "actuator": True,
        "valid": True,
        "model_version": 1,
    }


def episode(record_id, ended_at):
    return {
        "id": record_id,
        "started_at": (ended_at - timedelta(hours=2)).isoformat(),
        "ended_at": ended_at.isoformat(),
        "start_temperature": 18.0,
        "end_temperature": 21.0,
        "outside_mean": 5.0,
        "sample_count": 24,
        "valid": True,
        "model_version": 1,
    }


@pytest.mark.asyncio
async def test_checkpoint_coalesces_and_final_shutdown_flushes_newest(storage, factory):
    await storage.async_set_active("lounge", {"sequence": 1})
    checkpoint_store = factory.stores["zeal.thermal.active.entry"]
    assert checkpoint_store.delay == THERMAL_CHECKPOINT_INTERVAL_SECONDS

    await storage.async_set_active("lounge", {"sequence": 2})
    assert checkpoint_store.save_count == 0

    await checkpoint_store.flush_final_write()
    assert checkpoint_store.data["active"]["lounge"] == {"sequence": 2}
    assert checkpoint_store.save_count == 1


@pytest.mark.asyncio
async def test_important_transition_saves_immediately(storage, factory):
    await storage.async_set_active(
        "lounge", {"state": "heating"}, important_transition=True
    )
    checkpoint_store = factory.stores["zeal.thermal.active.entry"]
    assert checkpoint_store.data["active"]["lounge"]["state"] == "heating"


@pytest.mark.asyncio
async def test_room_history_is_lazy_deduplicated_and_bounded(storage, now, factory):
    samples = [
        sample(f"sample-{index}", now - timedelta(minutes=index * 5))
        for index in range(THERMAL_MAX_SAMPLES_PER_ROOM + 20)
    ]
    samples += [sample("sample-0", now)]
    samples += [sample("sample-0", now - timedelta(days=1))]
    samples += [sample("expired", now - timedelta(days=31))]
    episodes = [
        episode(f"episode-{index}", now - timedelta(hours=index * 8))
        for index in range(THERMAL_MAX_EPISODES_PER_ROOM + 20)
    ]
    episodes += [episode("expired", now - timedelta(days=366))]

    saved = await storage.async_save_room(
        "lounge", samples=samples, episodes=episodes
    )
    assert len(saved["samples"]) == THERMAL_MAX_SAMPLES_PER_ROOM
    assert len(saved["episodes"]) == THERMAL_MAX_EPISODES_PER_ROOM
    assert len({item["id"] for item in saved["samples"]}) == len(saved["samples"])
    newest_duplicate = next(
        item for item in saved["samples"] if item["id"] == "sample-0"
    )
    assert newest_duplicate["timestamp"] == now.isoformat()
    assert "zeal.thermal.room.entry.lounge" in factory.stores
    assert "zeal.thermal.room.entry.bedroom" not in factory.stores


@pytest.mark.asyncio
async def test_restart_loads_small_state_and_room_on_demand(storage, factory):
    await storage.async_set_active(
        "lounge", {"id": "active-1"}, important_transition=True
    )
    storage.models["lounge"] = {"confidence": 0.4}
    storage.room_ids.add("lounge")
    await storage.async_save_models()

    restored = ThermalStorage(None, "entry", store_factory=factory)
    await restored.async_load()
    assert restored.active["lounge"]["id"] == "active-1"
    assert restored.models["lounge"]["confidence"] == 0.4
    assert "zeal.thermal.room.entry.lounge" not in factory.stores


@pytest.mark.asyncio
async def test_reset_room_does_not_touch_other_rooms(storage, factory, now):
    await storage.async_save_room(
        "lounge", samples=[sample("l1", now)], episodes=[]
    )
    await storage.async_save_room(
        "bedroom", samples=[sample("b1", now)], episodes=[]
    )
    storage.models = {"lounge": {"x": 1}, "bedroom": {"x": 2}}
    storage.active = {"lounge": {"x": 1}, "bedroom": {"x": 2}}

    await storage.async_reset_room("lounge")
    assert factory.stores["zeal.thermal.room.entry.lounge"].removed
    assert not factory.stores["zeal.thermal.room.entry.bedroom"].removed
    assert "lounge" not in storage.models
    assert "bedroom" in storage.models
    assert "lounge" not in storage.active
    assert "bedroom" in storage.active


@pytest.mark.asyncio
async def test_reset_all_removes_every_known_store(storage, factory, now):
    await storage.async_save_room(
        "lounge", samples=[sample("l1", now)], episodes=[]
    )
    await storage.async_set_active(
        "bedroom", {"id": "active"}, important_transition=True
    )

    await storage.async_reset_all()
    assert factory.stores["zeal.thermal.room.entry.lounge"].removed
    assert factory.stores["zeal.thermal.room.entry.bedroom"].removed
    assert factory.stores["zeal.thermal.models.entry"].removed
    assert factory.stores["zeal.thermal.active.entry"].removed


@pytest.mark.asyncio
async def test_disable_keep_flushes_active_data_without_deleting(storage, factory):
    await storage.async_set_active("lounge", {"id": "active"})
    await storage.async_disable(delete_data=False)
    checkpoint = factory.stores["zeal.thermal.active.entry"]
    assert checkpoint.data["active"]["lounge"]["id"] == "active"
    assert not checkpoint.removed


@pytest.mark.asyncio
async def test_unknown_payload_version_is_not_overwritten(factory):
    model_store = factory(1, "zeal.thermal.models.entry", True)
    model_store.data = {"version": 99, "models": {"lounge": {"valuable": True}}}
    storage = ThermalStorage(None, "entry", store_factory=factory)

    with pytest.raises(ThermalStorageVersionError):
        await storage.async_load()
    assert model_store.data["models"]["lounge"]["valuable"] is True
    assert model_store.save_count == 0

    await storage.async_remove()
    assert model_store.removed
    assert factory.stores["zeal.thermal.room.entry.lounge"].removed


@pytest.mark.asyncio
async def test_malformed_room_records_are_safely_pruned(storage, factory, now):
    room_store = factory(1, "zeal.thermal.room.entry.lounge", False)
    room_store.data = {
        "version": 1,
        "samples": [
            {"id": "missing-time"},
            {"id": "naive", "timestamp": "2026-09-01T12:00:00"},
            sample("valid", now),
            "not-a-record",
        ],
        "episodes": "not-a-list",
    }

    history = await storage.async_load_room("lounge")
    assert [item["id"] for item in history["samples"]] == ["valid"]
    assert history["episodes"] == []


def test_eight_room_maximum_serialized_payload_is_below_planning_allowance(now):
    room = {
        "version": 1,
        "samples": [
            sample(f"sample-{index}", now - timedelta(minutes=index * 5))
            for index in range(THERMAL_MAX_SAMPLES_PER_ROOM)
        ],
        "episodes": [
            episode(f"episode-{index}", now - timedelta(hours=index * 12))
            for index in range(THERMAL_MAX_EPISODES_PER_ROOM)
        ],
    }
    eight_room_bytes = len(
        json.dumps(room, separators=(",", ":")).encode("utf-8")
    ) * 8
    assert eight_room_bytes < 20_000_000
    assert eight_room_bytes > 1_000_000
