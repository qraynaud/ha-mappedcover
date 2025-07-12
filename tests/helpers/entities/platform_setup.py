from typing import List
from unittest.mock import patch
from custom_components.mappedcover.cover import async_setup_entry
from tests.helpers.mocks.throttler import MockThrottler
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.mappedcover.cover import MappedCover


async def setup_platform_with_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry
) -> List[MappedCover]:
    """Helper to setup platform and return added entities.

    Args:
      hass: HomeAssistant instance
      config_entry: The config entry to use

    Returns:
      List of added MappedCover entities
    """
    added_entities = []

    async def mock_add_entities(entities, update_before_add=False):
        """Mock async_add_entities function that collects entities."""
        if entities:
            added_entities.extend(entities)

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        try:
            await async_setup_entry(hass, config_entry, mock_add_entities)
        except TypeError as e:
            if "NoneType" in str(e):
                # This suggests async_add_entities is None, which indicates
                # the test framework is calling the function differently
                raise RuntimeError(
                    f"async_add_entities was None when calling platform setup: {e}")
            else:
                raise

    return added_entities
