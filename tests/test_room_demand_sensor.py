"""Tests for recorded per-room effective heat-demand entities."""

from __future__ import annotations

from types import SimpleNamespace

from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.helpers import entity_registry as er

from custom_components.zeal.binary_sensor import ZealRoomDemandBinarySensor
from custom_components.zeal.const import (
    CONF_ZONES,
    DOMAIN,
    ROOM_ACTIVE,
    ROOM_ID,
    ROOM_NAME,
    ROOM_OPENING_SENSORS,
    ROOM_SENSORS,
    ROOM_TRVS,
    ZONE_ID,
    ZONE_NAME,
    ZONE_ROOMS,
    ZONE_SWITCH,
)
from custom_components.zeal.coordinator import RoomDemandStatus


class DemandCoordinator:
    """Minimum Coordinator surface used by the entity."""

    def __init__(self) -> None:
        self.data = {}
        self.last_update_success = True
        self.status = None

    def async_add_listener(self, _update_callback, _context=None):
        return lambda: None

    def room_demand_status(self, _room_id):
        return self.status


def test_room_demand_entity_exposes_binary_state_and_reason():
    coordinator = DemandCoordinator()
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entity = ZealRoomDemandBinarySensor(
        coordinator,
        entry,
        {ZONE_ID: "ground", ZONE_NAME: "Ground Floor"},
        {ROOM_ID: "lounge", ROOM_NAME: "Lounge"},
    )

    assert entity.unique_id == f"{entry.entry_id}_lounge_heat_demand"
    assert entity.is_on is None
    assert entity.extra_state_attributes == {"reason": "not_evaluated"}

    coordinator.status = RoomDemandStatus(
        "lounge",
        "Lounge",
        True,
        "demanding",
        setpoint=21.0,
        temperature=18.0,
    )
    assert entity.is_on is True
    assert entity.extra_state_attributes == {
        "reason": "demanding",
        "setpoint": 21.0,
        "temperature": 18.0,
        "open_entities": [],
    }

    coordinator.status = RoomDemandStatus(
        "lounge",
        "Lounge",
        False,
        "opening_open",
        open_entities=("binary_sensor.back_door",),
    )
    assert entity.is_on is False
    assert entity.extra_state_attributes["reason"] == "opening_open"
    assert entity.extra_state_attributes["open_entities"] == [
        "binary_sensor.back_door"
    ]


async def test_config_entry_creates_recordable_room_demand_entity(hass):
    room = {
        ROOM_ID: "lounge",
        ROOM_NAME: "Lounge",
        ROOM_TRVS: ["climate.lounge_trv"],
        ROOM_SENSORS: ["sensor.lounge_temperature"],
        ROOM_OPENING_SENSORS: [],
        ROOM_ACTIVE: True,
    }
    zone = {
        ZONE_ID: "ground",
        ZONE_NAME: "Ground Floor",
        ZONE_SWITCH: "switch.ground_pump",
        ZONE_ROOMS: [room],
    }
    hass.states.async_set("switch.ground_pump", "on")
    hass.states.async_set("climate.lounge_trv", "heat", {"temperature": 20.0})
    hass.states.async_set("sensor.lounge_temperature", "18.0")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="ZEAL HVAC System",
        data={},
        options={CONF_ZONES: [zone]},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_lounge_heat_demand"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"
    assert state.attributes["reason"] == "demanding"

    assert await hass.config_entries.async_unload(entry.entry_id)
