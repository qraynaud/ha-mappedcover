from custom_components.mappedcover.cover import MappedCover
from tests.helpers.entities.mocked_cover_manager import MockedCoverManager
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from typing import Tuple
from tests.helpers.mocks.throttler import MockThrottler
from unittest.mock import patch


def create_test_cover_with_throttler(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    entity_id: str = "cover.test_cover"
) -> Tuple[MappedCover, MockedCoverManager]:
    """Create a MappedCover with a mock cover manager and throttler for testing.

    Args:
      hass: HomeAssistant instance
      config_entry: Config entry for the test
      entity_id: Entity ID for the cover

    Returns:
      Tuple of (MappedCover, MockedCoverManager)
    """
    cover_manager = MockedCoverManager()

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        mapped_cover = MappedCover(
            hass, config_entry, entity_id, MockThrottler())
        cover_manager.add_cover(mapped_cover)

    return mapped_cover, cover_manager
