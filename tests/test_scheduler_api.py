"""Block 4 validation, persistence, audit and admin WebSocket tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zeal.const import (
    AUDIT_MAX_ENTRIES,
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
from custom_components.zeal.scheduler.audit import AuditLog
from custom_components.zeal.scheduler.configuration import (
    ConfigurationConflictError,
    async_save_hierarchy,
    async_save_schedule,
    configuration_revision,
    configuration_snapshot,
    export_configuration,
    validate_hierarchy,
)
from custom_components.zeal.scheduler.models import (
    WEEKDAYS,
    RoomSchedule,
    ScheduleConfiguration,
    SchedulePeriod,
)
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er


class MemoryStore:
    def __init__(self, data=None):
        self.data = data

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.data = data


def create_registry_fixture(hass):
    area = ar.async_get(hass).async_create("Living Room")
    registry = er.async_get(hass)
    switch = registry.async_get_or_create(
        "switch",
        "test",
        "heating_switch",
        suggested_object_id="heating_switch",
        original_name="Heating Switch",
    )
    trv = registry.async_get_or_create(
        "climate",
        "test",
        "living_trv",
        suggested_object_id="living_trv",
        original_name="Living TRV",
    )
    sensor = registry.async_get_or_create(
        "sensor",
        "test",
        "living_temperature",
        suggested_object_id="living_temperature",
        original_name="Living Temperature",
        original_device_class="temperature",
    )
    registry.async_update_entity(trv.entity_id, area_id=area.id)
    registry.async_update_entity(sensor.entity_id, area_id=area.id)
    zone = {
        ZONE_ID: "ground_floor",
        ZONE_NAME: "Ground Floor",
        ZONE_SWITCH: switch.entity_id,
        "heat_source": "ashp",
        "reenable_delay": 300,
        ZONE_ROOMS: [
            {
                ROOM_ID: area.id,
                ROOM_NAME: "Untrusted Browser Name",
                ROOM_TRVS: [trv.entity_id],
                ROOM_SENSORS: [sensor.entity_id],
                ROOM_ACTIVE: True,
            }
        ],
    }
    return area, switch, trv, sensor, zone


async def setup_loaded_entry(hass, zones):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="ZEAL HVAC System",
        data={},
        options={CONF_ZONES: zones},
    )
    entry.add_to_hass(hass)
    for zone in zones:
        if zone.get(ZONE_SWITCH):
            hass.states.async_set(zone[ZONE_SWITCH], "off")
        for room in zone.get(ZONE_ROOMS, []):
            for trv in room.get(ROOM_TRVS, []):
                hass.states.async_set(trv, "heat", {"temperature": 20.0})
            for sensor in room.get(ROOM_SENSORS, []):
                hass.states.async_set(sensor, "20.0")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def monday_schedule(room_id, room_name="Living Room", temperature=20):
    periods = (
        SchedulePeriod("morning", "morning", "Morning", "00:00", temperature),
    )
    return RoomSchedule(
        room_id,
        room_name,
        {day: periods if day == "monday" else () for day in WEEKDAYS},
    )


def test_revision_is_deterministic_and_changes_with_either_document():
    schedule = ScheduleConfiguration.empty()
    first = configuration_revision([], schedule)
    assert first == configuration_revision([], schedule)
    assert first != configuration_revision(
        [], ScheduleConfiguration(settings={"changed": True})
    )
    assert first != configuration_revision(
        [{ZONE_ID: "one"}], schedule
    )


def test_valid_hierarchy_is_normalized_from_home_assistant_registries(hass):
    area, switch, trv, sensor, zone = create_registry_fixture(hass)
    normalized = validate_hierarchy(hass, [zone])
    room = normalized[0][ZONE_ROOMS][0]
    assert room[ROOM_NAME] == area.name
    assert room[ROOM_TRVS] == [trv.entity_id]
    assert room[ROOM_SENSORS] == [sensor.entity_id]
    assert normalized[0][ZONE_SWITCH] == switch.entity_id


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda zones: zones.append(dict(zones[0])), "duplicate zone_id"),
        (
            lambda zones: zones[0][ZONE_ROOMS].append(dict(zones[0][ZONE_ROOMS][0])),
            "more than one zone",
        ),
        (lambda zones: zones[0].update({"reenable_delay": 3601}), "0 to 3600"),
        (lambda zones: zones[0].update({"reenable_delay": 1.5}), "whole number"),
        (lambda zones: zones[0].update({"heat_source": "nuclear"}), "invalid"),
        (lambda zones: zones[0].update({"ashp_capability": "unsafe"}), "invalid"),
    ],
)
def test_hierarchy_rejects_duplicates_and_invalid_controls(hass, mutate, match):
    _, _, _, _, zone = create_registry_fixture(hass)
    zones = [zone]
    mutate(zones)
    with pytest.raises(ValueError, match=match):
        validate_hierarchy(hass, zones)


def test_hierarchy_rejects_zeal_owned_thermostat_as_physical_trv(hass):
    _, _, trv, _, zone = create_registry_fixture(hass)
    registry = er.async_get(hass)
    registry.async_remove(trv.entity_id)
    own = registry.async_get_or_create(
        "climate",
        DOMAIN,
        "own_thermostat",
        suggested_object_id="own_thermostat",
    )
    registry.async_update_entity(
        own.entity_id, area_id=zone[ZONE_ROOMS][0][ROOM_ID]
    )
    zone[ZONE_ROOMS][0][ROOM_TRVS] = [own.entity_id]
    with pytest.raises(ValueError, match="ZEAL-owned"):
        validate_hierarchy(hass, [zone])


async def test_catalog_separates_zeal_targets_from_physical_room_equipment(hass):
    """Selectors cannot mix canonical ZEAL targets with physical devices."""
    area, _, trv, sensor, zone = create_registry_fixture(hass)
    entry = await setup_loaded_entry(hass, [zone])

    catalog = configuration_snapshot(hass, entry.entry_id)["catalog"]
    physical_ids = {
        item["entity_id"] for item in catalog["physical_room_thermostats"]
    }
    zeal_targets = catalog["zeal_room_thermostats"]
    sensor_ids = {item["entity_id"] for item in catalog["temperature_sensors"]}

    assert trv.entity_id in physical_ids
    assert sensor.entity_id in sensor_ids
    assert len(zeal_targets) == 1
    assert zeal_targets[0]["room_id"] == area.id
    assert zeal_targets[0]["zone_id"] == "ground_floor"
    assert zeal_targets[0]["entity_id"].startswith("climate.")
    assert zeal_targets[0]["entity_id"] not in physical_ids
    assert all(
        er.async_get(hass).async_get(entity_id).platform != DOMAIN
        for entity_id in (*physical_ids, *sensor_ids)
    )


async def test_schedule_save_updates_store_runtime_and_rejects_stale_revision(hass):
    area, _, _, _, zone = create_registry_fixture(hass)
    entry = await setup_loaded_entry(hass, [zone])
    snapshot = configuration_snapshot(hass, entry.entry_id)
    configuration = ScheduleConfiguration(
        rooms={area.id: monday_schedule(area.id)},
        settings={"saved": True},
        temperature_unit="°C",
    )
    new_revision = await async_save_schedule(
        hass,
        entry.entry_id,
        configuration,
        expected_revision=snapshot["revision"],
    )
    data = hass.data[DOMAIN][entry.entry_id]
    assert data["schedule_runtime"].configuration == configuration
    assert await data["schedule_storage"].async_load() == configuration
    assert new_revision != snapshot["revision"]
    with pytest.raises(ConfigurationConflictError):
        await async_save_schedule(
            hass,
            entry.entry_id,
            ScheduleConfiguration(settings={"stale": True}, temperature_unit="°C"),
            expected_revision=snapshot["revision"],
        )


async def test_configuration_export_is_json_safe_and_complete(hass):
    _, _, _, _, zone = create_registry_fixture(hass)
    entry = await setup_loaded_entry(hass, [zone])
    exported = export_configuration(hass, entry.entry_id)
    assert exported["format"] == "zeal-configuration"
    assert exported["entry_id"] == entry.entry_id
    assert exported["zones"][0][ZONE_ID] == "ground_floor"
    assert exported["schedule"]["version"] == 1
    assert "revision" in exported
    assert "generated_at" in exported


async def test_hierarchy_save_persists_and_survives_automatic_reload(hass):
    area, _, _, _, zone = create_registry_fixture(hass)
    entry = await setup_loaded_entry(hass, [zone])
    revision = configuration_snapshot(hass, entry.entry_id)["revision"]
    edited_zone = deepcopy(zone)
    edited_zone[ZONE_NAME] = "Renamed Ground Floor"
    zones, new_revision = await async_save_hierarchy(
        hass,
        entry.entry_id,
        [edited_zone],
        expected_revision=revision,
    )
    assert zones[0][ZONE_NAME] == "Renamed Ground Floor"
    assert new_revision != revision
    await hass.async_block_till_done()
    reloaded_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert reloaded_entry.options[CONF_ZONES][0][ZONE_NAME] == "Renamed Ground Floor"
    assert area.id in hass.data[DOMAIN][entry.entry_id][
        "schedule_runtime"
    ].configuration.rooms


async def test_audit_load_record_export_and_retention():
    store = MemoryStore(
        {
            "version": 1,
            "entries": [
                {"sequence": index} for index in range(AUDIT_MAX_ENTRIES + 1)
            ],
        }
    )
    audit = AuditLog(None, "entry", store=store)
    await audit.async_load()
    assert len(audit.export()["entries"]) == AUDIT_MAX_ENTRIES
    assert audit.export()["entries"][0]["sequence"] == 1
    await audit.async_record(
        timestamp=datetime(2026, 8, 24, 7, 0, tzinfo=timezone.utc),
        room_id="living_room",
        room_name="Living Room",
        canonical_entity_id="climate.zeal_living_room",
        previous_temperature=18,
        requested_temperature=20,
        cause="scheduled_transition",
        outcome="applied",
    )
    last = audit.export()["entries"][-1]
    assert last["room_id"] == "living_room"
    assert last["requested_temperature"] == 20.0
    assert len(store.data["entries"]) == AUDIT_MAX_ENTRIES


async def test_admin_websocket_reads_configuration_and_downloads(
    hass, hass_ws_client
):
    _, _, _, _, zone = create_registry_fixture(hass)
    entry = await setup_loaded_entry(hass, [zone])
    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": "zeal/get_configuration", "entry_id": entry.entry_id}
    )
    response = await client.receive_json()
    assert response["success"] is True
    assert response["result"]["entry_id"] == entry.entry_id
    assert response["result"]["catalog"]["areas"]

    await client.send_json_auto_id(
        {"type": "zeal/export_configuration", "entry_id": entry.entry_id}
    )
    response = await client.receive_json()
    assert response["success"] is True
    assert response["result"]["format"] == "zeal-configuration"

    await client.send_json_auto_id(
        {"type": "zeal/get_audit_log", "entry_id": entry.entry_id}
    )
    response = await client.receive_json()
    assert response["success"] is True
    assert response["result"]["maximum_entries"] == AUDIT_MAX_ENTRIES


async def test_admin_websocket_applies_and_clears_quick_change(hass, hass_ws_client):
    area, _, _, _, zone = create_registry_fixture(hass)
    entry = await setup_loaded_entry(hass, [zone])
    snapshot = configuration_snapshot(hass, entry.entry_id)
    schedule = ScheduleConfiguration(
        rooms={area.id: monday_schedule(area.id, temperature=20)},
        temperature_unit="°C",
    )
    await async_save_schedule(
        hass,
        entry.entry_id,
        schedule,
        expected_revision=snapshot["revision"],
    )
    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": "zeal/set_temporary_override",
            "entry_id": entry.entry_id,
            "room_ids": [area.id],
            "duration": "2h",
            "operation": "temperature",
            "value": 22,
        }
    )
    response = await client.receive_json()
    assert response["success"] is True
    room_state = response["result"]["rooms"][0]
    assert room_state["effective_temperature"] == 22
    assert room_state["override"]["duration"] == "2h"

    await client.send_json_auto_id(
        {
            "type": "zeal/clear_temporary_override",
            "entry_id": entry.entry_id,
            "room_id": area.id,
        }
    )
    response = await client.receive_json()
    assert response["success"] is True
    assert response["result"]["rooms"][0]["override"] is None
    assert hass.data[DOMAIN][entry.entry_id]["audit_log"].export()["entries"]


async def test_non_admin_websocket_is_rejected(
    hass, hass_ws_client, hass_read_only_access_token
):
    _, _, _, _, zone = create_registry_fixture(hass)
    entry = await setup_loaded_entry(hass, [zone])
    client = await hass_ws_client(access_token=hass_read_only_access_token)
    await client.send_json_auto_id(
        {"type": "zeal/get_configuration", "entry_id": entry.entry_id}
    )
    response = await client.receive_json()
    assert response["success"] is False
    assert response["error"]["code"] == "unauthorized"


async def test_websocket_rejects_stale_and_malformed_schedule_writes(
    hass, hass_ws_client
):
    area, _, _, _, zone = create_registry_fixture(hass)
    entry = await setup_loaded_entry(hass, [zone])
    client = await hass_ws_client()
    snapshot = configuration_snapshot(hass, entry.entry_id)
    bad_days = {day: [] for day in WEEKDAYS}
    bad_days["monday"] = [
        {
            "id": "bad",
            "friendly_name": "bad",
            "name": "Bad",
            "time": "25:00",
            "temperature": 20,
        }
    ]
    await client.send_json_auto_id(
        {
            "type": "zeal/update_room_days",
            "entry_id": entry.entry_id,
            "expected_revision": snapshot["revision"],
            "room_id": area.id,
            "days": bad_days,
        }
    )
    response = await client.receive_json()
    assert response["success"] is False
    assert response["error"]["code"] == "invalid_format"

    valid_days = {day: [] for day in WEEKDAYS}
    await client.send_json_auto_id(
        {
            "type": "zeal/update_room_days",
            "entry_id": entry.entry_id,
            "expected_revision": "stale-revision",
            "room_id": area.id,
            "days": valid_days,
        }
    )
    response = await client.receive_json()
    assert response["success"] is False
    assert response["error"]["code"] == "conflict"
