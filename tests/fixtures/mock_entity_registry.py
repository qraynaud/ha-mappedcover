"""Fixture for mock_entity_registry for mappedcover tests."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as get_entity_registry
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from tests.constants import TEST_ENTITY_NAME


@pytest.fixture
async def mock_entity_registry(hass: HomeAssistant, mock_device_registry):
    """Mock the entity registry with a source cover entity.

    Returns:
      tuple: (entity_registry, entity_id) containing the registry and created entity ID
    """
    device_registry, device_id = mock_device_registry

    entity_registry = get_entity_registry(hass)
    entry = entity_registry.async_get_or_create(
        COVER_DOMAIN,
        "test",
        "test_cover",
        device_id=device_id,
        original_name=TEST_ENTITY_NAME
    )

    return entity_registry, entry.entity_id
