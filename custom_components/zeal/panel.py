"""Register ZEAL's versioned, admin-only Home Assistant panel."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    PANEL_ASSET_VERSION,
    PANEL_COMPONENT,
    PANEL_STATIC_URL,
    PANEL_URL_PATH,
)

_STATIC_REGISTERED = f"{DOMAIN}_panel_static_registered"


def _panel_exists(hass: HomeAssistant) -> bool:
    """Return whether ZEAL's panel is registered across supported HA versions."""
    return PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {})


async def async_sync_panel(hass: HomeAssistant) -> None:
    """Expose the ZEAL configuration panel to administrators."""
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
        module_url=f"{PANEL_STATIC_URL}/zeal-panel.js?v={PANEL_ASSET_VERSION}",
        sidebar_title="ZEAL",
        sidebar_icon="mdi:radiator",
        require_admin=True,
        config_panel_domain=DOMAIN,
    )


async def async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the route after the final ZEAL entry unloads."""
    if _panel_exists(hass):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
