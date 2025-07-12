"""Fixture for mock_config_entry for mappedcover tests."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from tests.helpers import create_mock_config_entry
from tests.constants import TEST_ENTRY_ID, TEST_COVER_ID


@pytest.fixture
async def mock_config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Create a mock config entry and register it with Home Assistant.

    Returns:
      ConfigEntry: A standard test config entry
    """
    return await create_mock_config_entry(
        hass,
        entry_id=TEST_ENTRY_ID,
        covers=[TEST_COVER_ID]
    )
