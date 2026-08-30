"""Admin-only WebSocket boundary for ZEAL's future HTML panel."""

from __future__ import annotations

from typing import Any
from functools import wraps

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import Unauthorized

from ..const import (
    CONF_SHOW_IN_SIDEBAR,
    CONF_STANDARD_USER_QUICK_CHANGE,
    CONF_STANDARD_USER_SCHEDULE,
    DOMAIN,
)
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
        ws_get_zone_control,
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


def _require_feature(option: str):
    """Allow administrators, or standard users explicitly enabled in Setup."""
    def decorate(func):
        @wraps(func)
        def permitted(hass, connection, msg):
            user = connection.user
            entry = hass.config_entries.async_get_entry(msg.get("entry_id"))
            if user is None or entry is None or (
                not user.is_admin and not entry.options.get(option, False)
            ):
                raise Unauthorized
            return func(hass, connection, msg)

        return permitted

    return decorate


@websocket_api.websocket_command({vol.Required("type"): "zeal/list_entries"})
@callback
def ws_list_entries(hass, connection, msg) -> None:
    entries = [
        {"entry_id": entry.entry_id, "title": entry.title}
        for entry in hass.config_entries.async_entries(DOMAIN)
        if _loaded_entry(hass, entry.entry_id) is not None
    ]
    connection.send_result(msg["id"], {"entries": entries})


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


@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal/get_zone_control",
        vol.Required("entry_id"): str,
    }
)
@callback
def ws_get_zone_control(hass, connection, msg) -> None:
    data = _loaded_entry(hass, msg["entry_id"])
    if data is None:
        _send_not_found(connection, msg)
        return
    connection.send_result(
        msg["id"], {"zones": data["coordinator"].zone_control_snapshot()}
    )


@_require_feature(CONF_STANDARD_USER_SCHEDULE)
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


@_require_feature(CONF_STANDARD_USER_SCHEDULE)
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
        vol.Optional("show_in_sidebar"): bool,
        vol.Optional("standard_user_schedule"): bool,
        vol.Optional("standard_user_quick_change"): bool,
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
            show_in_sidebar=msg.get("show_in_sidebar"),
            standard_user_schedule=msg.get("standard_user_schedule"),
            standard_user_quick_change=msg.get("standard_user_quick_change"),
        )
    except ConfigurationConflictError as err:
        connection.send_error(msg["id"], ERR_CONFLICT, str(err))
        return
    except (KeyError, ValueError) as err:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(err))
        return
    connection.send_result(
        msg["id"],
        {
            "entry_id": msg["entry_id"],
            "revision": revision,
            "zones": zones,
            CONF_SHOW_IN_SIDEBAR: hass.config_entries.async_get_entry(
                msg["entry_id"]
            ).options.get(CONF_SHOW_IN_SIDEBAR, True),
            CONF_STANDARD_USER_SCHEDULE: hass.config_entries.async_get_entry(
                msg["entry_id"]
            ).options.get(CONF_STANDARD_USER_SCHEDULE, False),
            CONF_STANDARD_USER_QUICK_CHANGE: hass.config_entries.async_get_entry(
                msg["entry_id"]
            ).options.get(CONF_STANDARD_USER_QUICK_CHANGE, False),
        },
    )


@_require_feature(CONF_STANDARD_USER_QUICK_CHANGE)
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


@_require_feature(CONF_STANDARD_USER_QUICK_CHANGE)
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


@_require_feature(CONF_STANDARD_USER_QUICK_CHANGE)
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
