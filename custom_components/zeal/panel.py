"""Register ZEAL's versioned Home Assistant panel."""

from __future__ import annotations

import asyncio
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    CONF_SHOW_IN_SIDEBAR,
    DOMAIN,
    PANEL_ASSET_VERSION,
    PANEL_COMPONENT,
    PANEL_STATIC_URL,
    PANEL_URL_PATH,
)

_STATIC_REGISTERED = f"{DOMAIN}_panel_static_registered"
_PANEL_LOCK = f"{DOMAIN}_panel_lock"


def _panel_exists(hass: HomeAssistant) -> bool:
    """Return whether ZEAL's panel is registered across supported HA versions."""
    return PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {})


def _show_in_sidebar(hass: HomeAssistant) -> bool:
    """Show the shared link while any loaded ZEAL instance requests it."""
    for entry_id in hass.data.get(DOMAIN, {}):
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is not None and entry.options.get(CONF_SHOW_IN_SIDEBAR, True):
            return True
    return False


async def async_sync_panel(hass: HomeAssistant) -> None:
    """Expose ZEAL; its Setup view and configuration APIs remain admin-only."""
    lock = hass.data.setdefault(_PANEL_LOCK, asyncio.Lock())
    async with lock:
        show_in_sidebar = _show_in_sidebar(hass)
        if _panel_exists(hass):
            frontend.async_remove_panel(hass, PANEL_URL_PATH)
        if not hass.data.get(_STATIC_REGISTERED):
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        PANEL_STATIC_URL,
                        Path(__file__).parent / "frontend",
                        False,
                    )
                ]
            )
            hass.data[_STATIC_REGISTERED] = True
        await panel_custom.async_register_panel(
            hass=hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_COMPONENT,
            module_url=f"{PANEL_STATIC_URL}/zeal-panel-entry.js?v={PANEL_ASSET_VERSION}",
            sidebar_title="ZEAL" if show_in_sidebar else None,
            sidebar_icon="mdi:radiator" if show_in_sidebar else None,
            require_admin=False,
            config_panel_domain=DOMAIN if show_in_sidebar else None,
        )


async def async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the route after the final ZEAL entry unloads."""
    lock = hass.data.setdefault(_PANEL_LOCK, asyncio.Lock())
    async with lock:
        if _panel_exists(hass):
            frontend.async_remove_panel(hass, PANEL_URL_PATH)
