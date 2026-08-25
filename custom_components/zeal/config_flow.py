"""Minimal initial setup for the ZEAL HVAC System integration.

Zones, rooms and equipment are managed in ZEAL's admin-only HTML panel. The
panel is registered as this integration's configuration panel, replacing the
former multi-page Options Flow while preserving existing config-entry options.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow

from .const import CONF_ZONES, DOMAIN


class ZealConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create an initially empty ZEAL instance."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Name the instance; all detailed setup happens in the panel."""
        if user_input is not None:
            name = user_input["name"].strip()
            await self.async_set_unique_id(name.lower())
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=name,
                data={},
                options={CONF_ZONES: []},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("name", default="ZEAL HVAC System"): str}
            ),
        )
