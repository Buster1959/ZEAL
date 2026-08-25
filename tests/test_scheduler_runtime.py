"""ZEAL scheduler runtime and canonical room-boundary tests."""

from __future__ import annotations

from datetime import datetime

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zeal.const import (
    CONF_ZONES,
    DOMAIN,
    ROOM_ACTIVE,
    ROOM_ID,
    ROOM_NAME,
    ROOM_SENSORS,
    ROOM_TRVS,
    ZONE_ID,
    ZONE_NAME,
    ZONE_ROOMS,
    ZONE_SWITCH,
)
from custom_components.zeal.coordinator import ZealCoordinator
from custom_components.zeal.scheduler.models import (
    WEEKDAYS,
    RoomSchedule,
    ScheduleConfiguration,
    SchedulePeriod,
)
from custom_components.zeal.scheduler.runtime import ScheduleRuntime
from homeassistant.helpers.storage import Store


def schedule_room(
    room_id: str,
    room_name: str,
    monday_periods: tuple[SchedulePeriod, ...],
) -> RoomSchedule:
    return RoomSchedule(
        room_id,
        room_name,
        {
            day: monday_periods if day == "monday" else ()
            for day in WEEKDAYS
        },
    )


def schedule_configuration(*rooms: RoomSchedule) -> ScheduleConfiguration:
    return ScheduleConfiguration(rooms={room.room_id: room for room in rooms})


class FakeCoordinator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, float, str]] = []
        self.available: set[str] = set()
        self.listener = None
        self.listener_removed = False
        self.refreshes = 0

    def async_add_listener(self, listener):
        self.listener = listener

        def unsubscribe():
            self.listener_removed = True

        return unsubscribe

    async def async_set_room_target(self, room_id, temperature, *, source):
        self.calls.append((room_id, temperature, source))
        return room_id in self.available

    async def async_request_refresh(self):
        self.refreshes += 1


class FakeCanonicalThermostat:
    entity_id = "climate.zeal_living_room"

    def __init__(self) -> None:
        self.target_temperature = 20.0
        self.hvac_mode = "heat"
        self.applied: list[tuple[float, str]] = []

    def apply_target_setpoint(self, temperature, *, source):
        self.target_temperature = temperature
        self.applied.append((temperature, source))


def install_timer_capture(monkeypatch):
    scheduled: list[tuple[datetime, object]] = []
    cancellations: list[datetime] = []

    def fake_track(_hass, callback, when):
        scheduled.append((when, callback))

        def cancel():
            cancellations.append(when)

        return cancel

    monkeypatch.setattr(
        "custom_components.zeal.scheduler.runtime.event_helper.async_track_point_in_time",
        fake_track,
    )
    return scheduled, cancellations


async def test_startup_reconciles_only_stable_zeal_room_ids(hass, monkeypatch):
    now = datetime(2026, 8, 24, 12, 0)
    monkeypatch.setattr(
        "custom_components.zeal.scheduler.runtime.dt_util.now", lambda: now
    )
    install_timer_capture(monkeypatch)
    coordinator = FakeCoordinator()
    coordinator.available = {"living_room", "bedroom"}
    configuration = schedule_configuration(
        schedule_room(
            "living_room",
            "Living Room",
            (SchedulePeriod("morning", "morning", "Morning", "07:00", 20),),
        ),
        schedule_room(
            "bedroom",
            "Bedroom",
            (SchedulePeriod("morning", "morning", "Morning", "08:00", 18),),
        ),
    )
    runtime = ScheduleRuntime(hass, coordinator)
    await runtime.async_start(configuration)

    assert coordinator.calls == [
        ("living_room", 20.0, "startup_reconciliation"),
        ("bedroom", 18.0, "startup_reconciliation"),
    ]
    assert all(not room_id.startswith("climate.") for room_id, _, _ in coordinator.calls)
    assert coordinator.refreshes == 1


async def test_runtime_never_calls_home_assistant_climate_service_directly(
    hass, monkeypatch
):
    now = datetime(2026, 8, 24, 12, 0)
    monkeypatch.setattr(
        "custom_components.zeal.scheduler.runtime.dt_util.now", lambda: now
    )
    install_timer_capture(monkeypatch)
    coordinator = FakeCoordinator()
    coordinator.available = {"living_room"}
    service_calls = []

    async def capture_service(call):
        service_calls.append(call)

    hass.services.async_register("climate", "set_temperature", capture_service)
    runtime = ScheduleRuntime(hass, coordinator)
    await runtime.async_start(
        schedule_configuration(
            schedule_room(
                "living_room",
                "Living Room",
                (SchedulePeriod("morning", "morning", "Morning", "07:00", 20),),
            )
        )
    )
    assert service_calls == []
    assert coordinator.calls[0][0] == "living_room"


async def test_missing_thermostat_is_not_marked_applied_and_retries(
    hass, monkeypatch
):
    now = datetime(2026, 8, 24, 12, 0)
    monkeypatch.setattr(
        "custom_components.zeal.scheduler.runtime.dt_util.now", lambda: now
    )
    install_timer_capture(monkeypatch)
    coordinator = FakeCoordinator()
    runtime = ScheduleRuntime(hass, coordinator)
    await runtime.async_start(
        schedule_configuration(
            schedule_room(
                "living_room",
                "Living Room",
                (SchedulePeriod("morning", "morning", "Morning", "07:00", 20),),
            )
        )
    )
    assert len(coordinator.calls) == 1
    assert coordinator.refreshes == 0

    coordinator.available.add("living_room")
    coordinator.listener()
    await hass.async_block_till_done()
    assert len(coordinator.calls) == 2
    assert coordinator.calls[-1] == (
        "living_room",
        20.0,
        "availability_reconciliation",
    )
    assert coordinator.refreshes == 1

    coordinator.listener()
    await hass.async_block_till_done()
    assert len(coordinator.calls) == 2


async def test_runtime_schedules_the_nearest_room_transition(hass, monkeypatch):
    now = datetime(2026, 8, 24, 12, 0)
    monkeypatch.setattr(
        "custom_components.zeal.scheduler.runtime.dt_util.now", lambda: now
    )
    scheduled, _ = install_timer_capture(monkeypatch)
    coordinator = FakeCoordinator()
    coordinator.available = {"living_room", "bedroom"}
    runtime = ScheduleRuntime(hass, coordinator)
    await runtime.async_start(
        schedule_configuration(
            schedule_room(
                "living_room",
                "Living Room",
                (
                    SchedulePeriod("morning", "morning", "Morning", "07:00", 20),
                    SchedulePeriod("evening", "evening", "Evening", "18:00", 21),
                ),
            ),
            schedule_room(
                "bedroom",
                "Bedroom",
                (
                    SchedulePeriod("morning", "morning", "Morning", "08:00", 18),
                    SchedulePeriod("night", "night", "Night", "22:00", 16),
                ),
            ),
        )
    )
    assert scheduled[-1][0] == datetime(2026, 8, 24, 18, 0)


async def test_transition_applies_changed_period_and_reschedules(hass, monkeypatch):
    now = datetime(2026, 8, 24, 12, 0)
    monkeypatch.setattr(
        "custom_components.zeal.scheduler.runtime.dt_util.now", lambda: now
    )
    scheduled, _ = install_timer_capture(monkeypatch)
    coordinator = FakeCoordinator()
    coordinator.available = {"living_room"}
    runtime = ScheduleRuntime(hass, coordinator)
    await runtime.async_start(
        schedule_configuration(
            schedule_room(
                "living_room",
                "Living Room",
                (
                    SchedulePeriod("morning", "morning", "Morning", "07:00", 20),
                    SchedulePeriod("evening", "evening", "Evening", "18:00", 21),
                ),
            )
        )
    )
    callback = scheduled[-1][1]
    callback(datetime(2026, 8, 24, 18, 0))
    await hass.async_block_till_done()
    assert coordinator.calls[-1] == (
        "living_room",
        21.0,
        "scheduled_transition",
    )


async def test_stop_cancels_timer_and_coordinator_listener(hass, monkeypatch):
    now = datetime(2026, 8, 24, 12, 0)
    monkeypatch.setattr(
        "custom_components.zeal.scheduler.runtime.dt_util.now", lambda: now
    )
    _, cancellations = install_timer_capture(monkeypatch)
    coordinator = FakeCoordinator()
    coordinator.available = {"living_room"}
    runtime = ScheduleRuntime(hass, coordinator)
    await runtime.async_start(
        schedule_configuration(
            schedule_room(
                "living_room",
                "Living Room",
                (
                    SchedulePeriod("morning", "morning", "Morning", "07:00", 20),
                    SchedulePeriod("night", "night", "Night", "22:00", 17),
                ),
            )
        )
    )
    await runtime.async_stop()
    assert cancellations == [datetime(2026, 8, 24, 22, 0)]
    assert coordinator.listener_removed is True


async def test_coordinator_boundary_updates_canonical_then_guarded_physical_trv(hass):
    room_data = {
        ROOM_ID: "living_room",
        ROOM_NAME: "Living Room",
        ROOM_TRVS: ["climate.physical_trv"],
        ROOM_SENSORS: ["sensor.living_room"],
        ROOM_ACTIVE: True,
    }
    zone = {
        ZONE_ID: "ground_floor",
        ZONE_NAME: "Ground Floor",
        ZONE_SWITCH: "switch.ground_floor",
        ZONE_ROOMS: [room_data],
    }
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={CONF_ZONES: [zone]})
    entry.add_to_hass(hass)
    coordinator = ZealCoordinator(
        hass, entry, Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
    )
    thermostat = FakeCanonicalThermostat()
    coordinator.room_thermostats["living_room"] = thermostat
    hass.states.async_set("climate.physical_trv", "heat", {"temperature": 18.0})
    physical_calls = []

    async def capture_set_temperature(call):
        physical_calls.append(dict(call.data))

    hass.services.async_register("climate", "set_temperature", capture_set_temperature)
    applied = await coordinator.async_set_room_target(
        "living_room", 21.0, source="scheduled_transition"
    )
    assert applied is True
    assert thermostat.applied == [(21.0, "scheduled_transition")]
    assert physical_calls == [
        {"entity_id": "climate.physical_trv", "temperature": 21.0}
    ]


async def test_unknown_room_fails_without_any_physical_service_call(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={CONF_ZONES: []})
    entry.add_to_hass(hass)
    coordinator = ZealCoordinator(
        hass, entry, Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
    )
    calls = []

    async def capture_set_temperature(call):
        calls.append(call)

    hass.services.async_register("climate", "set_temperature", capture_set_temperature)
    assert (
        await coordinator.async_set_room_target(
            "missing_room", 21.0, source="scheduled_transition"
        )
        is False
    )
    assert calls == []


async def test_scheduled_target_is_clamped_at_canonical_room_boundary(hass):
    room_data = {
        ROOM_ID: "living_room",
        ROOM_NAME: "Living Room",
        ROOM_TRVS: ["climate.physical_trv"],
        ROOM_SENSORS: [],
        ROOM_ACTIVE: True,
    }
    zone = {
        ZONE_ID: "ground_floor",
        ZONE_NAME: "Ground Floor",
        ZONE_SWITCH: "switch.ground_floor",
        ZONE_ROOMS: [room_data],
    }
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={CONF_ZONES: [zone]})
    entry.add_to_hass(hass)
    coordinator = ZealCoordinator(
        hass, entry, Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
    )
    thermostat = FakeCanonicalThermostat()
    coordinator.room_thermostats["living_room"] = thermostat
    hass.states.async_set("climate.physical_trv", "heat", {"temperature": 18.0})
    written = []

    async def capture_set_temperature(call):
        written.append(call.data["temperature"])

    hass.services.async_register("climate", "set_temperature", capture_set_temperature)
    await coordinator.async_set_room_target(
        "living_room", 95.0, source="scheduled_transition"
    )
    assert thermostat.target_temperature == 30.0
    assert written == [30.0]


async def test_config_entry_setup_and_unload_own_scheduler_runtime(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="ZEAL HVAC System",
        data={},
        options={CONF_ZONES: []},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id) is True
    await hass.async_block_till_done()
    entry_data = hass.data[DOMAIN][entry.entry_id]
    assert "schedule_storage" in entry_data
    assert isinstance(entry_data["schedule_runtime"], ScheduleRuntime)
    assert entry_data["schedule_runtime"].configuration == ScheduleConfiguration.empty()

    assert await hass.config_entries.async_unload(entry.entry_id) is True
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
