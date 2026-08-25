"""Admin-only WebSocket boundary for ZEAL's future HTML panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from ..const import DOMAIN
from .configuration import (
    ConfigurationConflictError,
    async_save_away_mode,
    async_save_hierarchy,
    async_save_schedule,
    configuration_snapshot,
    export_configuration,
)
from .editor import copy_room_schedule, update_room_days

_REGISTERED = f"{DOMAIN}_scheduler_websocket_registered"
ERR_CONFLICT = "conflict"


def async_register_commands(hass: HomeAssistant) -> None:
    """Register commands once even when an entry reloads."""
    if hass.data.get(_REGISTERED):
        return
    for command in (
        ws_list_entries,
        ws_get_configuration,
        ws_update_room_days,
        ws_copy_room_schedule,
        ws_save_away_mode,
        ws_save_hierarchy,
        ws_get_quick_change,
        ws_set_temporary_override,
        ws_clear_temporary_override,
        ws_export_configuration,
        ws_get_audit_log,
    ):
        websocket_api.async_register_command(hass, command)
    hass.data[_REGISTERED] = True


def _loaded_entry(hass: HomeAssistant, entry_id: str) -> dict[str, Any] | None:
    return hass.data.get(DOMAIN, {}).get(entry_id)


def _send_not_found(connection, msg) -> None:
    connection.send_error(
        msg["id"], websocket_api.ERR_NOT_FOUND, "ZEAL config entry is not loaded"
    )


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "zeal/list_entries"})
@callback
def ws_list_entries(hass, connection, msg) -> None:
    entries = [
        {"entry_id": entry.entry_id, "title": entry.title}
        for entry in hass.config_entries.async_entries(DOMAIN)
        if _loaded_entry(hass, entry.entry_id) is not None
    ]
    connection.send_result(msg["id"], {"entries": entries})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal/get_configuration",
        vol.Required("entry_id"): str,
    }
)
@callback
def ws_get_configuration(hass, connection, msg) -> None:
    if _loaded_entry(hass, msg["entry_id"]) is None:
        _send_not_found(connection, msg)
        return
    connection.send_result(
        msg["id"], configuration_snapshot(hass, msg["entry_id"])
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal/update_room_days",
        vol.Required("entry_id"): str,
        vol.Required("expected_revision"): str,
        vol.Required("room_id"): str,
        vol.Required("days"): dict,
    }
)
@websocket_api.async_response
async def ws_update_room_days(hass, connection, msg) -> None:
    data = _loaded_entry(hass, msg["entry_id"])
    if data is None:
        _send_not_found(connection, msg)
        return
    try:
        updated = update_room_days(
            data["schedule_runtime"].configuration,
            msg["room_id"],
            msg["days"],
        )
        await async_save_schedule(
            hass,
            msg["entry_id"],
            updated,
            expected_revision=msg["expected_revision"],
        )
    except ConfigurationConflictError as err:
        connection.send_error(msg["id"], ERR_CONFLICT, str(err))
        return
    except KeyError:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Unknown room")
        return
    except ValueError as err:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(err))
        return
    connection.send_result(
        msg["id"], configuration_snapshot(hass, msg["entry_id"])
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal/copy_room_schedule",
        vol.Required("entry_id"): str,
        vol.Required("expected_revision"): str,
        vol.Required("source_room_id"): str,
        vol.Required("target_room_ids"): [str],
        vol.Required("source_days"): dict,
    }
)
@websocket_api.async_response
async def ws_copy_room_schedule(hass, connection, msg) -> None:
    data = _loaded_entry(hass, msg["entry_id"])
    if data is None:
        _send_not_found(connection, msg)
        return
    try:
        updated = copy_room_schedule(
            data["schedule_runtime"].configuration,
            msg["source_room_id"],
            msg["target_room_ids"],
            msg["source_days"],
        )
        await async_save_schedule(
            hass,
            msg["entry_id"],
            updated,
            expected_revision=msg["expected_revision"],
        )
    except ConfigurationConflictError as err:
        connection.send_error(msg["id"], ERR_CONFLICT, str(err))
        return
    except KeyError:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Unknown room")
        return
    except ValueError as err:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(err))
        return
    connection.send_result(
        msg["id"], configuration_snapshot(hass, msg["entry_id"])
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal/save_away_mode",
        vol.Required("entry_id"): str,
        vol.Required("expected_revision"): str,
        vol.Required("mode"): vol.In(["off", "calendar", "date_range"]),
        vol.Required("calendar_entity_id"): vol.Any(None, str),
        vol.Required("starts_at"): vol.Any(None, str),
        vol.Required("ends_at"): vol.Any(None, str),
        vol.Required("temperature"): vol.Coerce(float),
    }
)
@websocket_api.async_response
async def ws_save_away_mode(hass, connection, msg) -> None:
    if _loaded_entry(hass, msg["entry_id"]) is None:
        _send_not_found(connection, msg)
        return
    try:
        await async_save_away_mode(
            hass,
            msg["entry_id"],
            expected_revision=msg["expected_revision"],
            mode=msg["mode"],
            calendar_entity_id=msg["calendar_entity_id"],
            starts_at=msg["starts_at"],
            ends_at=msg["ends_at"],
            temperature=msg["temperature"],
        )
    except ConfigurationConflictError as err:
        connection.send_error(msg["id"], ERR_CONFLICT, str(err))
        return
    except ValueError as err:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(err))
        return
    connection.send_result(
        msg["id"], configuration_snapshot(hass, msg["entry_id"])
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal/save_hierarchy",
        vol.Required("entry_id"): str,
        vol.Required("expected_revision"): str,
        vol.Required("zones"): list,
    }
)
@websocket_api.async_response
async def ws_save_hierarchy(hass, connection, msg) -> None:
    if _loaded_entry(hass, msg["entry_id"]) is None:
        _send_not_found(connection, msg)
        return
    try:
        zones, revision = await async_save_hierarchy(
            hass,
            msg["entry_id"],
            msg["zones"],
            expected_revision=msg["expected_revision"],
        )
    except ConfigurationConflictError as err:
        connection.send_error(msg["id"], ERR_CONFLICT, str(err))
        return
    except (KeyError, ValueError) as err:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(err))
        return
    connection.send_result(
        msg["id"], {"entry_id": msg["entry_id"], "revision": revision, "zones": zones}
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal/get_quick_change",
        vol.Required("entry_id"): str,
    }
)
@callback
def ws_get_quick_change(hass, connection, msg) -> None:
    data = _loaded_entry(hass, msg["entry_id"])
    if data is None:
        _send_not_found(connection, msg)
        return
    connection.send_result(msg["id"], data["schedule_runtime"].quick_change_state())


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal/set_temporary_override",
        vol.Required("entry_id"): str,
        vol.Required("room_ids"): [str],
        vol.Required("duration"): vol.In(["2h", "4h", "next_change"]),
        vol.Required("operation"): vol.In(["delta", "temperature"]),
        vol.Required("value"): vol.Coerce(float),
    }
)
@websocket_api.async_response
async def ws_set_temporary_override(hass, connection, msg) -> None:
    data = _loaded_entry(hass, msg["entry_id"])
    if data is None:
        _send_not_found(connection, msg)
        return
    try:
        await data["schedule_runtime"].async_set_temporary_override(
            msg["room_ids"],
            duration=msg["duration"],
            operation=msg["operation"],
            value=msg["value"],
        )
    except ValueError as err:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(err))
        return
    connection.send_result(msg["id"], data["schedule_runtime"].quick_change_state())


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal/clear_temporary_override",
        vol.Required("entry_id"): str,
        vol.Required("room_id"): str,
    }
)
@websocket_api.async_response
async def ws_clear_temporary_override(hass, connection, msg) -> None:
    data = _loaded_entry(hass, msg["entry_id"])
    if data is None:
        _send_not_found(connection, msg)
        return
    try:
        await data["schedule_runtime"].async_clear_temporary_override(msg["room_id"])
    except ValueError as err:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(err))
        return
    connection.send_result(msg["id"], data["schedule_runtime"].quick_change_state())


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal/export_configuration",
        vol.Required("entry_id"): str,
    }
)
@callback
def ws_export_configuration(hass, connection, msg) -> None:
    if _loaded_entry(hass, msg["entry_id"]) is None:
        _send_not_found(connection, msg)
        return
    connection.send_result(msg["id"], export_configuration(hass, msg["entry_id"]))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal/get_audit_log",
        vol.Required("entry_id"): str,
    }
)
@callback
def ws_get_audit_log(hass, connection, msg) -> None:
    data = _loaded_entry(hass, msg["entry_id"])
    if data is None:
        _send_not_found(connection, msg)
        return
    connection.send_result(msg["id"], data["audit_log"].export())
