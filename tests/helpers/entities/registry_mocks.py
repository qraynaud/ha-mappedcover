from homeassistant.helpers.area_registry import async_get as get_area_registry
from homeassistant.helpers.device_registry import async_get as get_device_registry
from homeassistant.helpers.entity_registry import async_get as get_entity_registry
from custom_components.mappedcover.const import DOMAIN
from typing import Dict
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from tests.constants import TEST_AREA_ID, TEST_DEVICE_NAME, TEST_ENTITY_NAME, TEST_COVER_ID


async def setup_mock_registries(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    area_name: str = TEST_AREA_ID,
    device_name: str = TEST_DEVICE_NAME,
    entity_name: str = TEST_ENTITY_NAME,
    source_entity_id: str = TEST_COVER_ID
) -> Dict:
    """Set up mock area, device, and entity registries.

    Args:
      hass: HomeAssistant instance
      config_entry: The config entry to associate with
      area_name: Name for the test area
      device_name: Name for the test device
      entity_name: Name for the test entity
      source_entity_id: Entity ID to use as source

    Returns:
      Dict containing registry objects and their created entries
    """
    # Create area
    area_registry = get_area_registry(hass)
    area = area_registry.async_create(area_name)

    # Create device
    device_registry = get_device_registry(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("cover", "test_source_device")},
        name=device_name,
        manufacturer="Test Manufacturer",
        model="Test Model"
    )

    # Associate device with area
    device_registry.async_update_device(device.id, area_id=area.id)

    # Create entity
    entity_registry = get_entity_registry(hass)
    entity = entity_registry.async_get_or_create(
        DOMAIN,
        "",
        source_entity_id.split(".", 1)[1],
        device_id=device.id,
        original_name=entity_name
    )

    return {
        "area_registry": area_registry,
        "area": area,
        "device_registry": device_registry,
        "device": device,
        "entity_registry": entity_registry,
        "entity": entity
    }
