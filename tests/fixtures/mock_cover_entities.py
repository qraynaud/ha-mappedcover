"""Fixture for mock_cover_entities for mappedcover tests."""
import pytest
from homeassistant.core import HomeAssistant
from tests.helpers import create_standard_mock_covers


@pytest.fixture
async def mock_cover_entities(hass: HomeAssistant):
    """Set up mock mappedcover entities in the state machine.

    Returns:
      None: Sets up standard cover entities in Home Assistant
    """
    create_standard_mock_covers(hass)
    yield
