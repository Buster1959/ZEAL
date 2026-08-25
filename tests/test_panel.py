"""Block 5 panel registration and frontend contract tests."""

from __future__ import annotations

from pathlib import Path

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zeal.const import CONF_ZONES, DOMAIN, PANEL_URL_PATH
from homeassistant.components import frontend
from homeassistant.data_entry_flow import FlowResultType


PANEL_FILE = (
    Path(__file__).parents[1]
    / "custom_components"
    / "zeal"
    / "frontend"
    / "zeal-panel.js"
)


async def test_initial_flow_only_names_an_empty_instance(hass):
    """Detailed heating setup belongs to the panel, not a multi-page flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "My ZEAL"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My ZEAL"
    assert result["data"] == {}
    assert result["options"] == {CONF_ZONES: []}


async def test_empty_entry_registers_admin_configuration_panel_and_asset(hass):
    """A fresh install immediately exposes the HTML setup surface."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="ZEAL HVAC System",
        data={},
        options={CONF_ZONES: []},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert frontend.async_panel_exists(hass, PANEL_URL_PATH)
    panel = hass.data[frontend.DATA_PANELS][PANEL_URL_PATH].to_response()
    assert panel["require_admin"] is True
    assert panel["config_panel_domain"] == DOMAIN
    assert panel["show_in_sidebar"] is True
    assert panel["component_name"] == "custom"
    assert panel["config"]["_panel_custom"]["name"] == "zeal-panel"
    assert panel["config"]["_panel_custom"]["module_url"].endswith(
        "/zeal-panel.js?v=2"
    )

    static_routes = {
        resource.canonical for resource in hass.http.app.router.resources()
    }
    assert "/zeal_static" in static_routes
    assert PANEL_FILE.is_file()

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert not frontend.async_panel_exists(hass, PANEL_URL_PATH)


def test_frontend_contains_setup_safety_and_responsive_contracts():
    """Protect the Block 5 features that are not executable in pytest's DOM."""
    source = PANEL_FILE.read_text()
    assert 'type: "zeal/list_entries"' in source
    assert 'type: "zeal/get_configuration"' in source
    assert 'type: "zeal/save_hierarchy"' in source
    assert "zeal_room_thermostats" in source
    assert "catalog.physical_room_thermostats" in source
    assert "catalog.climate_entities" not in source
    assert "Zone/Floor scheduling targets" in source
    assert "It is never offered below as a physical thermostat" in source
    assert "expected_revision: this._configuration.revision" in source
    assert "Every zone needs a name" in source
    assert "Do not assign a thermostat to more than one thermostat setpoint scheduler" in source
    assert "another integration, automation, blueprint or schedule" in source
    assert "@media (max-width: 760px)" in source
    assert "@media (max-width: 430px)" in source
