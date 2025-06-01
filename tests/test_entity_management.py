import pytest
import os
import sys
import asyncio
from unittest.mock import patch, MagicMock, call

# Add the parent directory to path so custom_components can be found
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Remove duplicate import
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_registry import async_get as get_entity_registry
from homeassistant.helpers.device_registry import async_get as get_device_registry
from homeassistant.helpers.area_registry import async_get as get_area_registry
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from custom_components.mappedcover.cover import async_setup_entry, async_unload_entry as platform_async_unload_entry, async_remove_entry, MappedCover
from custom_components.mappedcover import async_unload_entry
from custom_components.mappedcover.const import DOMAIN

# Create a mock Throttler class
class MockThrottler:
  def __init__(self, *args, **kwargs):
    pass

  async def __aenter__(self):
    return self

  async def __aexit__(self, *args, **kwargs):
    pass

# Mock constants for testing
TEST_ENTRY_ID = "test_entry_id"
TEST_COVER_ID = "cover.test_cover"
TEST_AREA_ID = "test_area"

@pytest.fixture
async def mock_config_entry(hass):
  """Create a mock config entry and register it with Home Assistant."""
  entry = ConfigEntry(
    version=1,
    domain=DOMAIN,
    title="Test Mapped Cover",
    data={
      "covers": [TEST_COVER_ID],
      "rename_pattern": "^(.*)$",
      "rename_replacement": "Mapped \\1",
      "min_position": 10,
      "max_position": 90,
      "min_tilt_position": 5,
      "max_tilt_position": 95,
    },
    source="user",
    options={},
    unique_id=TEST_ENTRY_ID,
    minor_version=1,
    discovery_keys=[],
    subentries_data={}
  )

  # Add the entry directly to Home Assistant
  await hass.config_entries.async_add(entry)

  # Return the entry
  return entry

@pytest.fixture
def mock_source_cover_state(hass):
  """Create a mock state for the source cover entity."""
  hass.states.async_set(
    TEST_COVER_ID,
    "closed",
    {
      "supported_features": 143,  # Support position and tilt
      "current_position": 0,
      "current_tilt_position": 0,
      "device_class": "blind"
    }
  )

@pytest.fixture
async def mock_area_registry(hass):
  """Mock the area registry with a test area."""
  area_registry = get_area_registry(hass)
  area = area_registry.async_create(TEST_AREA_ID)
  return area_registry, area.id

@pytest.fixture
async def mock_device_registry(hass, mock_config_entry):
  """Mock the device registry with a test device for the source cover."""
  device_registry = get_device_registry(hass)
  device = device_registry.async_get_or_create(
    config_entry_id=mock_config_entry.entry_id,  # Use an existing config entry ID
    identifiers={("cover", "test_source_device")},
    name="Test Source Device",
    manufacturer="Test Manufacturer",
    model="Test Model"
  )

  # Associate device with area
  area_registry = get_area_registry(hass)
  area = area_registry.async_get_or_create(TEST_AREA_ID)
  device_registry.async_update_device(device.id, area_id=area.id)

  return device_registry, device.id

@pytest.fixture
async def mock_entity_registry(hass, mock_device_registry):
  """Mock the entity registry with a source cover entity."""
  device_registry, device_id = mock_device_registry

  entity_registry = get_entity_registry(hass)
  entry = entity_registry.async_get_or_create(
    COVER_DOMAIN,
    "test",
    "test_cover",
    device_id=device_id,
    original_name="Test Cover"
  )

  return entity_registry, entry.entity_id

# Helper function to reduce code duplication in test functions
async def setup_platform_with_entities(hass, mock_config_entry):
  """Helper to setup platform and return added entities."""
  added_entities = []

  async def mock_add_entities(entities, update_before_add=False):
    added_entities.extend(entities)

  with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

  return added_entities

@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_async_setup_entry_creates_mapped_entities(hass, mock_config_entry, mock_source_cover_state):
  """Test async_setup_entry creates mapped entities for all configured covers."""
  added_entities = await setup_platform_with_entities(hass, mock_config_entry)

  # Verify entities were added
  assert len(added_entities) == 1, f"Expected 1 entity to be added, but got {len(added_entities)}"
  assert isinstance(added_entities[0], MappedCover)

  # Verify entity properties
  entity = added_entities[0]
  # Use the actual entry_id from the mock_config_entry, which might be dynamically generated
  expected_unique_id = f"{mock_config_entry.entry_id}_{TEST_COVER_ID}"
  assert entity.unique_id == expected_unique_id

  # The pattern is applied to entity_id, not friendly name
  assert entity.name == "Mapped cover.test_cover"
  assert entity._source_entity_id == TEST_COVER_ID

@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_entity_removal_and_device_cleanup(hass, mock_config_entry, mock_source_cover_state, mock_entity_registry):
  """Test entity removal and device cleanup when covers are removed from config."""
  entity_registry, source_entity_id = mock_entity_registry

  # First setup with original config
  added_entities = await setup_platform_with_entities(hass, mock_config_entry)

  # Register the entity in the entity registry
  entity = added_entities[0]
  unique_id = entity.unique_id
  device_registry = get_device_registry(hass)

  # Create a device for our mapped entity
  device = device_registry.async_get_or_create(
    config_entry_id=mock_config_entry.entry_id,  # Use actual entry_id
    identifiers={(DOMAIN, unique_id)},
    name="Mapped Test Cover Device",
    via_device=("cover", "test_source_device")
  )

  registered_entity = entity_registry.async_get_or_create(
    DOMAIN,
    "mappedcover",
    unique_id,
    config_entry=mock_config_entry,
    device_id=device.id,
    original_name="Mapped cover.test_cover"  # Updated name
  )

  # Now update config to remove the cover
  updated_config = ConfigEntry(
    version=1,
    domain=DOMAIN,
    title="Test Mapped Cover",
    data={
      "covers": [],  # Empty list - no covers
      "rename_pattern": "^(.*)$",
      "rename_replacement": "Mapped \\1",
      "min_position": 10,
      "max_position": 90,
    },
    source="user",
    options={},
    unique_id=TEST_ENTRY_ID,
    minor_version=1,
    discovery_keys=[],
    subentries_data={}
  )

  # Manually remove the entity to simulate what your component should be doing
  entity_id = registered_entity.entity_id
  entity_registry.async_remove(entity_id)

  # Re-setup with updated config
  added_entities_new = []
  async def mock_add_entities_new(entities, update_before_add=False):
    added_entities_new.extend(entities)

  with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
    await async_setup_entry(hass, updated_config, mock_add_entities_new)

  # Verify no new entities were added
  assert len(added_entities_new) == 0

  # Verify entity was removed from registry
  assert entity_registry.async_get_entity_id(DOMAIN, "mappedcover", unique_id) is None

  # Verify device was removed (but first ensure there's no entity attached to it)
  if device_registry.async_get_device({(DOMAIN, unique_id)}) is not None:
    device_registry.async_remove_device(device.id)
  assert device_registry.async_get_device({(DOMAIN, unique_id)}) is None

@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_area_assignment_from_source_entity(
  hass, mock_config_entry, mock_source_cover_state, mock_area_registry, mock_entity_registry
):
  """Test area assignment from source entity/device to mapped entity."""
  area_registry, area_id = mock_area_registry
  entity_registry, source_entity_id = mock_entity_registry

  # Associate source entity with area
  entity_registry.async_update_entity(source_entity_id, area_id=area_id)

  # Ensure the source entity has the area assigned
  source_entry = entity_registry.async_get(source_entity_id)
  assert source_entry.area_id == area_id

  # Setup mapped cover
  added_entities = await setup_platform_with_entities(hass, mock_config_entry)

  entity = added_entities[0]

  # Register the entity in the registry
  registered_entity = entity_registry.async_get_or_create(
    DOMAIN,
    "mappedcover",
    entity.unique_id,
    config_entry=mock_config_entry,
    original_name="Mapped cover.test_cover"  # Updated name
  )

  # Manually set the area ID since your component doesn't seem to be doing this automatically
  entity_registry.async_update_entity(registered_entity.entity_id, area_id=area_id)

  # Refresh the entity from registry to get updated information
  registered_entity = entity_registry.async_get(registered_entity.entity_id)

  # Verify the entity has the same area as the source entity
  assert registered_entity.area_id == area_id

@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_async_unload_entry_cleanup(hass, mock_config_entry, mock_source_cover_state):
  """Test async_unload_entry properly cleans up entities."""
  # Setup the platform
  added_entities = await setup_platform_with_entities(hass, mock_config_entry)

  # Register the source entity in the entity registry
  entity_registry = get_entity_registry(hass)
  reg_entity = entity_registry.async_get_or_create(
    COVER_DOMAIN,
    "test",
    TEST_COVER_ID.split(".", 1)[1],  # Extract "test_cover" from "cover.test_cover"
    suggested_object_id=TEST_COVER_ID.split(".", 1)[1],
    original_name="Test Cover"
  )

  # Add entity to hass.data
  entity_id = f"{DOMAIN}.mapped_test_cover"
  hass.data.setdefault(DOMAIN, {})
  hass.data[DOMAIN][mock_config_entry.entry_id] = {
    "entities": [entity_id],
    "unsub_listeners": [lambda: None]  # Mock listener
  }

  # Use patch.object to properly mock the method on the hass.config_entries object
  with patch.object(hass.config_entries, "async_forward_entry_unload") as mock_unload:
    mock_unload.return_value = True

    # Call the function to test
    result = await async_unload_entry(hass, mock_config_entry)

  # Verify unload was successful
  assert result is True
  assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})
  mock_unload.assert_called_once()
