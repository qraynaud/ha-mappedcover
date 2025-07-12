"""Fixture for full_mock_setup for mappedcover tests."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from tests.helpers import (
    create_mock_cover_entity,
    setup_mock_registries,
)
from tests.constants import TEST_AREA_ID, TEST_DEVICE_NAME, TEST_ENTITY_NAME, TEST_COVER_ID


@pytest.fixture
async def full_mock_setup(hass: HomeAssistant, mock_config_entry: ConfigEntry):
    """Complete mock setup with registries, entities, and cleanup.

    This fixture provides a complete test environment with all necessary
    components set up, including source entities, registries, and config entries.

    Returns:
      dict: Setup data including config entry and registries
    """
    # Setup all registries
    registries = await setup_mock_registries(
        hass,
        mock_config_entry,
        area_name=TEST_AREA_ID,
        device_name=TEST_DEVICE_NAME,
        entity_name=TEST_ENTITY_NAME,
        source_entity_id=TEST_COVER_ID
    )

    # Create the source cover state
    create_mock_cover_entity(hass, TEST_COVER_ID)

    yield {
        "config_entry": mock_config_entry,
        "registries": registries,
    }
