"""Validated persistence boundary shared by ZEAL's panel APIs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from ..const import (
    CONF_ZONES,
    DEFAULT_REENABLE_DELAY,
    DOMAIN,
    HEAT_SOURCE_ASHP,
    HEAT_SOURCE_DEFAULT_REENABLE_DELAY,
    HEAT_SOURCE_OPTIONS,
    ROOM_ACTIVE,
    ROOM_COOLING_CAPABLE,
    ROOM_ID,
    ROOM_NAME,
    ROOM_SENSORS,
    ROOM_TRVS,
    ASHP_CAPABILITY_HEAT_AND_COOL,
    ASHP_CAPABILITY_HEAT_ONLY,
    ZONE_ASHP_CAPABILITY,
    ZONE_HEAT_SOURCE,
    ZONE_ID,
    ZONE_NAME,
    ZONE_REENABLE_DELAY,
    ZONE_ROOMS,
    ZONE_SWITCH,
)
from .models import ScheduleConfiguration
from .rooms import reconcile_room_schedules


class ConfigurationConflictError(ValueError):
    """Raised when a browser tries to save an obsolete document."""


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, allow_nan=False))


def configuration_revision(
    zones: list[dict[str, Any]], schedule: ScheduleConfiguration
) -> str:
    """Return a stable optimistic-concurrency token for both saved documents."""
    payload = json.dumps(
        {"zones": zones, "schedule": schedule.to_dict()},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def _entry_data(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    data = hass.data.get(DOMAIN, {}).get(entry_id)
    if data is None:
        raise KeyError(entry_id)
    return data


def current_revision(hass: HomeAssistant, entry_id: str) -> str:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        raise KeyError(entry_id)
    data = _entry_data(hass, entry_id)
    return configuration_revision(
        list(entry.options.get(CONF_ZONES, [])),
        data["schedule_runtime"].configuration,
    )


def configuration_snapshot(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    """Return the complete non-secret state required by the future panel."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        raise KeyError(entry_id)
    data = _entry_data(hass, entry_id)
    schedule = data["schedule_runtime"].configuration
    zones = _json_copy(list(entry.options.get(CONF_ZONES, [])))
    return {
        "entry_id": entry_id,
        "title": entry.title,
        "revision": configuration_revision(zones, schedule),
        "zones": zones,
        "schedule": schedule.to_dict(),
        "quick_change": data["schedule_runtime"].quick_change_state(),
        "catalog": configuration_catalog(hass, entry_id),
    }


def configuration_catalog(
    hass: HomeAssistant, entry_id: str
) -> dict[str, list[dict[str, Any]]]:
    """Return separate canonical and physical equipment catalogs.

    ZEAL's generated room thermostats are the only climate entities exposed as
    scheduling targets. They are deliberately kept out of the physical room
    thermostat catalog, where selecting one would make ZEAL drive itself.
    """
    area_registry = ar.async_get(hass)
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    areas = sorted(
        (
            {"area_id": area.id, "name": area.name}
            for area in area_registry.async_list_areas()
        ),
        key=lambda item: item["name"].casefold(),
    )
    catalog: dict[str, list[dict[str, Any]]] = {
        "areas": areas,
        "switches": [],
        "zeal_room_thermostats": [],
        "physical_room_thermostats": [],
        "temperature_sensors": [],
    }
    for entity in entity_registry.entities.values():
        if entity.disabled_by is not None or entity.platform == DOMAIN:
            continue
        area_id = entity.area_id
        if area_id is None and entity.device_id:
            device = device_registry.async_get(entity.device_id)
            area_id = device.area_id if device else None
        item = {
            "entity_id": entity.entity_id,
            "name": entity.name or entity.original_name or entity.entity_id,
            "area_id": area_id,
        }
        if entity.domain == "switch":
            catalog["switches"].append(item)
        elif entity.domain == "climate":
            catalog["physical_room_thermostats"].append(item)
        elif entity.domain == "sensor" and (
            entity.device_class or entity.original_device_class
        ) == "temperature":
            catalog["temperature_sensors"].append(item)
    data = _entry_data(hass, entry_id)
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        raise KeyError(entry_id)
    for zone in entry.options.get(CONF_ZONES, []):
        for room in zone.get(ZONE_ROOMS, []):
            thermostat = data["coordinator"].room_thermostats.get(room[ROOM_ID])
            entity_id = getattr(thermostat, "entity_id", None)
            if not entity_id:
                continue
            registry_entry = entity_registry.async_get(entity_id)
            catalog["zeal_room_thermostats"].append(
                {
                    "entity_id": entity_id,
                    "name": (
                        (registry_entry.name or registry_entry.original_name)
                        if registry_entry
                        else getattr(thermostat, "name", entity_id)
                    )
                    or entity_id,
                    "room_id": room[ROOM_ID],
                    "zone_id": zone[ZONE_ID],
                }
            )
    for key in (
        "switches",
        "zeal_room_thermostats",
        "physical_room_thermostats",
        "temperature_sensors",
    ):
        catalog[key].sort(
            key=lambda item: (str(item["name"]).casefold(), item["entity_id"])
        )
    return catalog


def export_configuration(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    """Build a directly downloadable, JSON-safe configuration document."""
    return {
        "format": "zeal-configuration",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **configuration_snapshot(hass, entry_id),
    }


def _require_name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _require_unique_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ValueError(f"{field} must be a list of entity IDs")
    if len(set(value)) != len(value):
        raise ValueError(f"{field} contains duplicate entity IDs")
    return list(value)


def validate_hierarchy(
    hass: HomeAssistant, raw_zones: Any
) -> list[dict[str, Any]]:
    """Validate the complete Zone -> Area/Room -> equipment document."""
    if not isinstance(raw_zones, list):
        raise ValueError("zones must be a list")
    area_registry = ar.async_get(hass)
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    zone_ids: set[str] = set()
    room_ids: set[str] = set()
    used_switches: set[str] = set()
    used_room_entities: set[str] = set()
    normalized: list[dict[str, Any]] = []

    def registry_entity(entity_id: str, domain: str, field: str):
        entity = entity_registry.async_get(entity_id)
        if entity is None or entity.domain != domain:
            raise ValueError(f"{field} contains an unknown {domain} entity: {entity_id}")
        if entity.platform == DOMAIN:
            raise ValueError(f"{field} cannot contain a ZEAL-owned entity: {entity_id}")
        if entity.disabled_by is not None:
            raise ValueError(f"{field} contains a disabled entity: {entity_id}")
        return entity

    def effective_area_id(entity) -> str | None:
        if entity.area_id is not None:
            return entity.area_id
        device = device_registry.async_get(entity.device_id) if entity.device_id else None
        return device.area_id if device else None

    for zone_index, raw_zone in enumerate(raw_zones):
        if not isinstance(raw_zone, Mapping):
            raise ValueError(f"zones[{zone_index}] must be an object")
        zone_id = _require_name(raw_zone.get(ZONE_ID), f"zones[{zone_index}].zone_id")
        if zone_id in zone_ids:
            raise ValueError(f"duplicate zone_id: {zone_id}")
        zone_ids.add(zone_id)
        name = _require_name(raw_zone.get(ZONE_NAME), f"zones[{zone_index}].name")
        switch = raw_zone.get(ZONE_SWITCH) or None
        if switch is not None:
            if not isinstance(switch, str):
                raise ValueError(f"zones[{zone_index}].switch must be an entity ID")
            registry_entity(switch, "switch", f"zones[{zone_index}].switch")
            if switch in used_switches:
                raise ValueError(f"zone switch is assigned more than once: {switch}")
            used_switches.add(switch)
        heat_source = raw_zone.get(ZONE_HEAT_SOURCE, HEAT_SOURCE_ASHP)
        if heat_source not in HEAT_SOURCE_OPTIONS:
            raise ValueError(f"zones[{zone_index}].heat_source is invalid")
        delay = raw_zone.get(
            ZONE_REENABLE_DELAY,
            HEAT_SOURCE_DEFAULT_REENABLE_DELAY.get(
                heat_source, DEFAULT_REENABLE_DELAY
            ),
        )
        if (
            isinstance(delay, bool)
            or not isinstance(delay, (int, float))
            or not float(delay).is_integer()
        ):
            raise ValueError(
                f"zones[{zone_index}].reenable_delay must be a whole number"
            )
        if not 0 <= float(delay) <= 3600:
            raise ValueError(f"zones[{zone_index}].reenable_delay must be 0 to 3600")
        raw_rooms = raw_zone.get(ZONE_ROOMS, [])
        if not isinstance(raw_rooms, list):
            raise ValueError(f"zones[{zone_index}].rooms must be a list")
        rooms: list[dict[str, Any]] = []
        for room_index, raw_room in enumerate(raw_rooms):
            field = f"zones[{zone_index}].rooms[{room_index}]"
            if not isinstance(raw_room, Mapping):
                raise ValueError(f"{field} must be an object")
            room_id = _require_name(raw_room.get(ROOM_ID), f"{field}.room_id")
            area = area_registry.async_get_area(room_id)
            if area is None:
                raise ValueError(f"{field}.room_id is not a Home Assistant Area")
            if room_id in room_ids:
                raise ValueError(f"Area is assigned to more than one zone: {room_id}")
            room_ids.add(room_id)
            trvs = _require_unique_strings(raw_room.get(ROOM_TRVS, []), f"{field}.trvs")
            sensors = _require_unique_strings(
                raw_room.get(ROOM_SENSORS, []), f"{field}.sensors"
            )
            for entity_id in trvs:
                entity = registry_entity(entity_id, "climate", f"{field}.trvs")
                if effective_area_id(entity) != room_id:
                    raise ValueError(f"{entity_id} does not belong to Area {room_id}")
            for entity_id in sensors:
                entity = registry_entity(entity_id, "sensor", f"{field}.sensors")
                device_class = entity.device_class or entity.original_device_class
                if device_class != "temperature":
                    raise ValueError(f"{entity_id} is not a temperature sensor")
                if effective_area_id(entity) != room_id:
                    raise ValueError(f"{entity_id} does not belong to Area {room_id}")
            duplicates = used_room_entities.intersection((*trvs, *sensors))
            if duplicates:
                raise ValueError(
                    "room equipment is assigned more than once: "
                    + ", ".join(sorted(duplicates))
                )
            used_room_entities.update((*trvs, *sensors))
            active = raw_room.get(ROOM_ACTIVE, True)
            if not isinstance(active, bool):
                raise ValueError(f"{field}.active must be true or false")
            cooling_capable = raw_room.get(ROOM_COOLING_CAPABLE, False)
            if not isinstance(cooling_capable, bool):
                raise ValueError(
                    f"{field}.cooling_capable must be true or false"
                )
            rooms.append(
                {
                    ROOM_ID: room_id,
                    ROOM_NAME: area.name,
                    ROOM_TRVS: trvs,
                    ROOM_SENSORS: sensors,
                    ROOM_ACTIVE: active,
                    ROOM_COOLING_CAPABLE: cooling_capable,
                }
            )
        capability = raw_zone.get(
            ZONE_ASHP_CAPABILITY, ASHP_CAPABILITY_HEAT_ONLY
        )
        if capability not in (
            ASHP_CAPABILITY_HEAT_ONLY,
            ASHP_CAPABILITY_HEAT_AND_COOL,
        ):
            raise ValueError(f"zones[{zone_index}].ashp_capability is invalid")
        normalized.append(
            {
                ZONE_ID: zone_id,
                ZONE_NAME: name,
                ZONE_SWITCH: switch,
                ZONE_HEAT_SOURCE: heat_source,
                ZONE_REENABLE_DELAY: int(delay),
                ZONE_ASHP_CAPABILITY: capability,
                ZONE_ROOMS: rooms,
            }
        )
    return normalized


async def async_save_schedule(
    hass: HomeAssistant,
    entry_id: str,
    configuration: ScheduleConfiguration,
    *,
    expected_revision: str,
) -> str:
    """Persist validated schedule data and update the live runtime atomically."""
    if current_revision(hass, entry_id) != expected_revision:
        raise ConfigurationConflictError("Configuration changed; reload and try again")
    data = _entry_data(hass, entry_id)
    await data["schedule_storage"].async_save(configuration)
    await data["schedule_runtime"].async_set_configuration(configuration)
    return current_revision(hass, entry_id)


async def async_save_hierarchy(
    hass: HomeAssistant,
    entry_id: str,
    raw_zones: Any,
    *,
    expected_revision: str,
) -> tuple[list[dict[str, Any]], str]:
    """Validate/save hierarchy, reconcile schedules, then trigger safe reload."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        raise KeyError(entry_id)
    if current_revision(hass, entry_id) != expected_revision:
        raise ConfigurationConflictError("Configuration changed; reload and try again")
    zones = validate_hierarchy(hass, raw_zones)
    data = _entry_data(hass, entry_id)
    current_schedule = data["schedule_runtime"].configuration
    configured_rooms = {
        room[ROOM_ID]: room[ROOM_NAME]
        for zone in zones
        for room in zone[ZONE_ROOMS]
        if room[ROOM_TRVS]
    }
    schedule = reconcile_room_schedules(current_schedule, configured_rooms)
    await data["schedule_storage"].async_save(schedule)
    hass.config_entries.async_update_entry(entry, options={CONF_ZONES: zones})
    return zones, configuration_revision(zones, schedule)
