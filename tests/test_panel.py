"""Block 5/6 panel registration and frontend contract tests."""

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
        "/zeal-panel.js?v=5"
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


def test_frontend_contains_visual_scheduler_contracts():
    """Protect the Block 6 interactions that require a browser DOM."""
    source = PANEL_FILE.read_text()
    assert 'data-view="schedule"' in source
    assert "Seven-day schedule" in source
    assert 'type: "zeal/update_room_days"' in source
    assert 'type: "zeal/copy_room_schedule"' in source
    assert "expected_revision: this._configuration.revision" in source
    assert "ZEAL scheduling target" in source
    assert "The schedule changes this ZEAL thermostat only" in source
    assert "timeline-point" in source
    assert "pointerdown" in source
    assert "Continues from the previous scheduled day" in source
    assert "Apply to selected days" in source
    assert "Copy this seven-day schedule to other rooms" in source
    assert "Their zone, Area, physical equipment and ZEAL thermostat remain unchanged" in source


def test_frontend_contains_quick_change_and_download_contracts():
    """Protect Block 7 selection, hold and browser-download interactions."""
    source = PANEL_FILE.read_text()
    assert 'data-view="quick"' in source
    assert 'type: "zeal/get_quick_change"' in source
    assert 'type: "zeal/set_temporary_override"' in source
    assert 'type: "zeal/clear_temporary_override"' in source
    assert "Select whole house" in source
    assert "Select zone" in source
    assert "Saved weekly schedules are never edited" in source
    assert "Until next scheduled change" in source
    assert 'type: "zeal/export_configuration"' in source
    assert 'type: "zeal/get_audit_log"' in source
    assert 'this._downloadJson("zeal-configuration"' in source
    assert 'this._downloadJson("zeal-audit"' in source
    assert "do not contain Home Assistant credentials or tokens" in source
    assert "new Blob" in source


def test_frontend_contains_away_mode_and_precedence_contracts():
    """Protect Block 8's mutually exclusive sources and safety messaging."""
    source = PANEL_FILE.read_text()
    assert 'type: "zeal/save_away_mode"' in source
    assert 'value="off"' in source
    assert 'value="calendar"' in source
    assert 'value="date_range"' in source
    assert 'type="datetime-local"' in source
    assert "Home Assistant's configured time zone" in source
    assert "Only active rooms receive this target" in source
    assert "Zone Manual Override remains the highest authority" in source
    assert "Use weekly schedules and Quick Change normally" in source
    assert "Quick Change is unavailable while Away mode is active" in source
    assert "End Away now" in source
