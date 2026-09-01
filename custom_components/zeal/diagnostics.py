"""Diagnostics support for ZEAL.

Answers "what is currently configured" directly from the integration's own
UI (Settings -> Devices & Services -> ZEAL HVAC System -> the "..." menu on
the integration card -> Download diagnostics) rather than requiring anyone
to inspect each Setup card or dig through debug logs. This was directly
motivated by a real
debugging session where the lack of any such view made a config mistake
(a ZealRoomThermostat entity accidentally selected as its own room's TRV,
causing infinite propagation recursion - see the Decisions Log) much
harder to spot than it needed to be.

This is HA's standard, idiomatic mechanism for "let a user see what an
integration currently holds" and complements the HTML Overview with a
portable troubleshooting document.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    ROOM_ACTIVE,
    ROOM_ID,
    ROOM_SENSORS,
    ROOM_TRVS,
    ZONE_HEAT_SOURCE,
    ZONE_ID,
    ZONE_REENABLE_DELAY,
    ZONE_ROOMS,
    ZONE_SWITCH,
)
from .coordinator import ZealCoordinator

# Defence in depth for future schema additions. Current diagnostics deliberately
# omit readable names, entity IDs, schedules and evidence before this standard
# Home Assistant redaction pass runs.
TO_REDACT = {"access_token", "api_key", "password", "secret", "token"}


def _schedule_summary(configuration, room_aliases: dict[str, str]) -> dict[str, Any]:
    """Summarise schedule shape without exposing times or temperatures."""
    rooms: dict[str, Any] = {}
    for room_id, room in configuration.rooms.items():
        alias = room_aliases.get(room_id, "unconfigured_room")
        period_counts = {day: len(periods) for day, periods in room.days.items()}
        rooms[alias] = {
            "period_count": sum(period_counts.values()),
            "period_counts_by_day": period_counts,
        }
    return {
        "room_count": len(rooms),
        "temperature_unit": configuration.temperature_unit,
        "rooms": rooms,
    }


def _away_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Retain operational Away status while omitting dates and entities."""
    return {
        "mode": state.get("mode"),
        "status": state.get("status"),
        "active": state.get("active", False),
    }


def _quick_change_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Count holds without exposing their rooms, targets or expiry times."""
    rooms = state.get("rooms", [])
    return {
        "room_count": len(rooms),
        "active_hold_count": sum(
            1 for room in rooms if isinstance(room, dict) and room.get("override")
        ),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: ZealCoordinator = entry_data["coordinator"]

    zones_snapshot: list[dict[str, Any]] = []
    room_aliases: dict[str, str] = {}
    for zone_index, zone in enumerate(coordinator.zones, start=1):
        zone_alias = f"zone_{zone_index}"
        zone_id = zone.get(ZONE_ID)
        switch_entity = zone.get(ZONE_SWITCH)
        switch_state = hass.states.get(switch_entity) if switch_entity else None

        rooms_snapshot: list[dict[str, Any]] = []
        for room_index, room in enumerate(zone.get(ZONE_ROOMS, []), start=1):
            room_id = room.get(ROOM_ID)
            room_alias = f"{zone_alias}_room_{room_index}"
            room_aliases[str(room_id)] = room_alias
            thermostat = coordinator.room_thermostats.get(room_id)

            trv_snapshot = []
            for trv_index, trv in enumerate(room.get(ROOM_TRVS, []) or [], start=1):
                state = hass.states.get(trv)
                trv_snapshot.append(
                    {
                        "entity": f"trv_{trv_index}",
                        "state": state.state if state else "not_found",
                        "target_temperature": (
                            state.attributes.get("temperature") if state else None
                        ),
                        "is_zeal_own_entity": trv
                        in coordinator.own_thermostat_entity_ids(),
                    }
                )

            sensor_snapshot = []
            for sensor_index, sensor in enumerate(
                room.get(ROOM_SENSORS, []) or [], start=1
            ):
                state = hass.states.get(sensor)
                sensor_snapshot.append(
                    {
                        "entity": f"temperature_sensor_{sensor_index}",
                        "state": state.state if state else "not_found",
                    }
                )

            rooms_snapshot.append(
                {
                    "room": room_alias,
                    "active": room.get(ROOM_ACTIVE, True),
                    "trvs": trv_snapshot,
                    "sensors": sensor_snapshot,
                    "computed_room_temperature": coordinator.room_current_temperature(
                        room_id
                    ),
                    "thermostat": {
                        "entity": "canonical_thermostat",
                        "target_temperature": getattr(
                            thermostat, "target_temperature", None
                        ),
                        "hvac_mode": getattr(thermostat, "hvac_mode", None),
                        "registered_with_coordinator": thermostat is not None,
                    }
                    if thermostat is not None
                    else {"registered_with_coordinator": False},
                }
            )

        zones_snapshot.append(
            {
                "zone": zone_alias,
                "heat_source": zone.get(ZONE_HEAT_SOURCE),
                "reenable_delay": zone.get(ZONE_REENABLE_DELAY),
                "switch": {
                    "entity": "heating_actuator",
                    "state": switch_state.state if switch_state else "not_found",
                },
                "override_active": getattr(
                    coordinator.override_switches.get(zone_id), "is_on", None
                ),
                "rooms": rooms_snapshot,
            }
        )

    runtime = entry_data["schedule_runtime"]
    learning = entry_data["schedule_learning"].snapshot()
    payload = {
        "entry": {
            "version": entry.version,
        },
        "zones": zones_snapshot,
        "schedule_summary": _schedule_summary(
            runtime.configuration, room_aliases
        ),
        "away_summary": _away_summary(runtime.away_mode_state()),
        "quick_change_summary": _quick_change_summary(
            runtime.quick_change_state()
        ),
        "learning_summary": {
            "version": learning["version"],
            "event_count": len(learning["events"]),
            "event_outcomes": dict(Counter(str(item.get("outcome", "unknown")) for item in learning["events"])),
            "proposal_count": len(learning["proposals"]),
            "proposal_statuses": dict(Counter(str(item.get("status", "unknown")) for item in learning["proposals"])),
        },
    }
    return async_redact_data(payload, TO_REDACT)
