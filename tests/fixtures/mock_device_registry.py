"""Fixture for mock_device_registry for mappedcover tests."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import async_get as get_device_registry
from homeassistant.helpers.area_registry import async_get as get_area_registry
from tests.constants import TEST_DEVICE_NAME, TEST_AREA_ID


@pytest.fixture
async def mock_device_registry(hass: HomeAssistant, mock_config_entry: ConfigEntry):
    """Mock the device registry with a test device for the source cover.

    Returns:
      tuple: (device_registry, device_id) containing the registry and created device ID
    """
    device_registry = get_device_registry(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={("cover", "test_source_device")},
        name=TEST_DEVICE_NAME,
        manufacturer="Test Manufacturer",
        model="Test Model"
    )

    # Associate device with area
    area_registry = get_area_registry(hass)
    area = area_registry.async_get_or_create(TEST_AREA_ID)
    device_registry.async_update_device(device.id, area_id=area.id)

    return device_registry, device.id
