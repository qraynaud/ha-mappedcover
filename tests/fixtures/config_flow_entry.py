
"""Fixture for config_flow_entry for mappedcover tests."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from tests.helpers import create_config_flow_entry, cleanup_platform_timers


@pytest.fixture
async def config_flow_entry(hass: HomeAssistant, mock_cover_entities) -> ConfigEntry:
    """Create a config entry for mappedcover through the normal config flow.

    Returns:
      ConfigEntry: Config entry created through the config flow
    """
    entry = await create_config_flow_entry(
        hass,
        label="Test Mapped Cover",
        covers=["cover.real_mappedcover"],
    )
    yield entry
    await cleanup_platform_timers(hass)
