"""Shared fixtures for mappedcover tests."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_registry import async_get as get_entity_registry
from homeassistant.helpers.device_registry import async_get as get_device_registry
from homeassistant.helpers.area_registry import async_get as get_area_registry
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN

# Use direct imports - conftest.py handles the path setup
from tests.helpers import (
  create_mock_config_entry,
  create_mock_cover_entity,
  setup_mock_registries,
  create_standard_mock_covers,
  cleanup_platform_timers,
  TEST_ENTRY_ID,
  TEST_COVER_ID,
  TEST_AREA_ID,
  TEST_DEVICE_NAME,
  TEST_ENTITY_NAME,
)
from custom_components.mappedcover.const import DOMAIN


@pytest.fixture
async def mock_config_entry(hass: HomeAssistant) -> ConfigEntry:
  """Create a mock config entry and register it with Home Assistant."""
  return await create_mock_config_entry(
    hass,
    entry_id=TEST_ENTRY_ID,
    covers=[TEST_COVER_ID]
  )


@pytest.fixture
def mock_source_cover_state(hass: HomeAssistant):
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
async def mock_cover_entities(hass: HomeAssistant):
  """Set up mock mappedcover entities in the state machine."""
  create_standard_mock_covers(hass)
  yield


@pytest.fixture
async def mock_area_registry(hass: HomeAssistant):
  """Mock the area registry with a test area."""
  area_registry = get_area_registry(hass)
  area = area_registry.async_create(TEST_AREA_ID)
  return area_registry, area.id


@pytest.fixture
async def mock_device_registry(hass: HomeAssistant, mock_config_entry: ConfigEntry):
  """Mock the device registry with a test device for the source cover."""
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


@pytest.fixture
async def mock_entity_registry(hass: HomeAssistant, mock_device_registry):
  """Mock the entity registry with a source cover entity."""
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


@pytest.fixture
async def full_mock_setup(hass: HomeAssistant, mock_config_entry: ConfigEntry):
  """Complete mock setup with registries, entities, and cleanup."""
  # Create the source cover state
  await create_mock_cover_entity(hass, TEST_COVER_ID)

  # Setup all registries
  registries = await setup_mock_registries(
    hass,
    mock_config_entry,
    area_name=TEST_AREA_ID,
    device_name=TEST_DEVICE_NAME,
    entity_name=TEST_ENTITY_NAME,
    source_entity_id=TEST_COVER_ID
  )

  yield {
    "config_entry": mock_config_entry,
    "registries": registries,
  }

  # Cleanup platform timers after each test
  await cleanup_platform_timers(hass)


@pytest.fixture
async def config_flow_entry(hass: HomeAssistant, mock_cover_entities):
  """Create a config entry for mappedcover through the normal config flow."""
  from tests.helpers import create_config_flow_entry

  entry = await create_config_flow_entry(
    hass,
    label="Test Mapped Cover",
    covers=["cover.real_mappedcover"],
  )

  yield entry

  # Cleanup platform timers after each test
  await cleanup_platform_timers(hass)


@pytest.fixture(autouse=True)
async def cleanup_timers(hass: HomeAssistant):
  """Automatically cleanup platform timers after each test."""
  yield
  await cleanup_platform_timers(hass)
