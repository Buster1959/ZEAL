"""Minimal initial setup for the ZEAL HVAC System integration.

Zones, rooms and equipment are managed in ZEAL's admin-only HTML panel. The
panel is registered as this integration's configuration panel, replacing the
former multi-page Options Flow while preserving existing config-entry options.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .const import CONF_SHOW_IN_SIDEBAR, CONF_ZONES, DOMAIN


class ZealConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create an initially empty ZEAL instance."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> ZealOptionsFlow:
        """Provide a native recovery route when the ZEAL panel is hidden."""
        return ZealOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Name the instance; all detailed setup happens in the panel."""
        if user_input is not None:
            name = user_input["name"].strip()
            return self.async_create_entry(
                title=name,
                data={},
                options={CONF_ZONES: [], CONF_SHOW_IN_SIDEBAR: True},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("name", default="ZEAL HVAC System"): str}
            ),
        )


class ZealOptionsFlow(OptionsFlow):
    """Manage access to ZEAL's full HTML panel from native HA settings."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Show the sidebar recovery preference."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    **self.config_entry.options,
                    CONF_SHOW_IN_SIDEBAR: user_input[CONF_SHOW_IN_SIDEBAR],
                }
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SHOW_IN_SIDEBAR,
                        default=self.config_entry.options.get(
                            CONF_SHOW_IN_SIDEBAR, True
                        ),
                    ): bool
                }
            ),
        )
