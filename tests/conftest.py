"""Shared pytest fixtures for the ZEAL test suite."""
import threading

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


# The pinned custom-component plugin predates Home Assistant Core's allowance
# for pycares' transient DNS safe-shutdown thread. Match Core's current cleanup
# policy exactly so WebSocket tests do not report this dependency-owned daemon
# as a ZEAL thread leak; every other newly created thread remains visible.
_threading_enumerate = threading.enumerate


def _enumerate_without_pycares_shutdown_thread():
    return [
        thread
        for thread in _threading_enumerate()
        if "_run_safe_shutdown_loop" not in thread.name
    ]


threading.enumerate = _enumerate_without_pycares_shutdown_thread


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Required by pytest-homeassistant-custom-component so hass will
    actually load a custom_components/ integration instead of only the
    ones bundled with HA core."""
    yield
