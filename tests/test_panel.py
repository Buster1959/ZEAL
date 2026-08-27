"""Block 5/6 panel registration and frontend contract tests."""

from __future__ import annotations

from pathlib import Path

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zeal.const import (
    CONF_SHOW_IN_SIDEBAR,
    CONF_ZONES,
    DOMAIN,
    PANEL_URL_PATH,
)
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
    assert result["options"] == {
        CONF_ZONES: [],
        CONF_SHOW_IN_SIDEBAR: True,
    }


async def test_flow_allows_separate_named_instances_and_rejects_duplicate_names(hass):
    """A boiler and ASHP can have independent entries on one HA machine."""
    for name in ("Boiler ZEAL", "ASHP ZEAL"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"name": name}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY

    duplicate = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    duplicate = await hass.config_entries.flow.async_configure(
        duplicate["flow_id"], {"name": "boiler zeal"}
    )
    assert duplicate["type"] is FlowResultType.ABORT
    assert duplicate["reason"] == "already_configured"


async def test_native_options_flow_can_restore_a_hidden_sidebar_link(hass):
    """Home Assistant Configure can recover access when the panel is hidden."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hidden ZEAL",
        data={},
        options={CONF_ZONES: [], CONF_SHOW_IN_SIDEBAR: False},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SHOW_IN_SIDEBAR: True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_ZONES: [],
        CONF_SHOW_IN_SIDEBAR: True,
    }


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

    assert PANEL_URL_PATH in hass.data[frontend.DATA_PANELS]
    panel = hass.data[frontend.DATA_PANELS][PANEL_URL_PATH].to_response()
    assert panel["require_admin"] is True
    assert panel["config_panel_domain"] == DOMAIN
    assert panel["title"] == "ZEAL"
    assert panel["component_name"] == "custom"
    assert panel["config"]["_panel_custom"]["name"] == "zeal-panel"
    assert panel["config"]["_panel_custom"]["module_url"].endswith(
        "/zeal-panel.js?v=9"
    )

    static_routes = {
        resource.canonical for resource in hass.http.app.router.resources()
    }
    assert "/zeal_static" in static_routes
    assert PANEL_FILE.is_file()

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert PANEL_URL_PATH not in hass.data.get(frontend.DATA_PANELS, {})


async def test_hidden_sidebar_keeps_the_integration_configuration_panel(hass):
    """The Configure route remains available when the sidebar link is hidden."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hidden ZEAL",
        data={},
        options={CONF_ZONES: [], CONF_SHOW_IN_SIDEBAR: False},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    panel = hass.data[frontend.DATA_PANELS][PANEL_URL_PATH].to_response()
    assert panel["title"] is None
    assert panel["config_panel_domain"] is None


async def test_shared_sidebar_link_follows_all_loaded_instances(hass):
    """Any opted-in instance keeps the single shared ZEAL link visible."""
    hidden = MockConfigEntry(
        domain=DOMAIN,
        title="Hidden ZEAL",
        data={},
        options={CONF_ZONES: [], CONF_SHOW_IN_SIDEBAR: False},
    )
    visible = MockConfigEntry(
        domain=DOMAIN,
        title="Visible ZEAL",
        data={},
        options={CONF_ZONES: [], CONF_SHOW_IN_SIDEBAR: True},
    )
    hidden.add_to_hass(hass)
    visible.add_to_hass(hass)

    assert await hass.config_entries.async_setup(hidden.entry_id)
    await hass.async_block_till_done()
    panel = hass.data[frontend.DATA_PANELS][PANEL_URL_PATH].to_response()
    assert panel["title"] == "ZEAL"

    assert await hass.config_entries.async_unload(visible.entry_id)
    panel = hass.data[frontend.DATA_PANELS][PANEL_URL_PATH].to_response()
    assert panel["title"] is None
    assert panel["config_panel_domain"] is None

    assert await hass.config_entries.async_unload(hidden.entry_id)
    assert PANEL_URL_PATH not in hass.data.get(frontend.DATA_PANELS, {})


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
    assert 'data-action="sidebar-toggle"' in source
    assert "Show ZEAL in the Home Assistant sidebar" in source
    assert "show_in_sidebar: this._showInSidebar" in source
    assert "Settings → Devices & Services → ZEAL HVAC System → Configure" in source
    assert "ZEAL instance management" in source
    assert "Delete this ZEAL instance" in source
    assert 'this._hass.callApi(\n        "delete"' in source
    assert "config/config_entries/entry/" in source
    assert "Other ZEAL instances are not removed" in source
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
    assert "Select all days" in source
    assert "Clear all days" in source
    assert 'data-schedule-action="toggle-target-days"' in source
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
    assert 'type="datetime-local" step="300"' in source
    assert "every active room in all zones" in source
    assert "Home Assistant's configured time zone" in source
    assert "Only active rooms receive this target" in source
    assert "Zone Manual Override remains the highest authority" in source
    assert "Use weekly schedules and Quick Change normally" in source
    assert "Quick Change is unavailable while Away mode is active" in source
    assert "End Away now" in source


def test_frontend_places_safety_warning_once_at_the_page_bottom():
    """The shared warning follows the selected page instead of interrupting it."""
    source = PANEL_FILE.read_text()
    assert source.count("${this._warning()}") == 1
    content = source[source.index("  _content() {") : source.index("  _header() {")]
    assert content.index("${this._warning()}") > content.index("this._renderOverview()")


def test_frontend_refreshes_schedule_navigation_after_setup_reload():
    """A slow config-entry reload must not leave a newly added zone hidden."""
    source = PANEL_FILE.read_text()
    assert 'if (next === "schedule" || next === "overview") {' in source
    assert "await this._loadConfiguration({ preserveNotice: true });" in source
    assert 'data-action="refresh-configuration"' in source
    assert "for (let attempt = 0; attempt < 40; attempt += 1)" in source
    assert "No ZEAL target change recorded yet" in source
    assert "Last change ${this._formatChangeTime" in source
