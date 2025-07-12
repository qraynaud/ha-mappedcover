"""Fixture for mock_area_registry for mappedcover tests."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as get_area_registry
from tests.constants import TEST_AREA_ID


@pytest.fixture
async def mock_area_registry(hass: HomeAssistant):
    """Mock the area registry with a test area.

    Returns:
      tuple: (area_registry, area_id) containing the registry and created area ID
    """
    area_registry = get_area_registry(hass)
    area = area_registry.async_create(TEST_AREA_ID)
    return area_registry, area.id
