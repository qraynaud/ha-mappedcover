"""Test entity creation and initialization for MappedCover."""
import pytest
import re
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as get_entity_registry
from homeassistant.helpers.device_registry import async_get as get_device_registry
from custom_components.mappedcover.cover import MappedCover
from custom_components.mappedcover.const import DOMAIN

from tests.helpers import create_mock_config_entry, create_mock_cover_entity, MockThrottler
from tests.fixtures import *  # Import all shared fixtures


@pytest.mark.asyncio
async def test_mapped_cover_init(hass: HomeAssistant, full_mock_setup, cleanup_timers):
  """Test MappedCover initialization with all required parameters."""
  setup_data = full_mock_setup
  config_entry = setup_data["config_entry"]

  # Create a throttler for the test
  throttler = MockThrottler()

  # Create the MappedCover entity
  mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", throttler)

  # Test basic initialization
  assert mapped_cover.hass is hass
  assert mapped_cover._entry is config_entry
  assert mapped_cover._source_entity_id == "cover.test_cover"
  assert mapped_cover._throttler is throttler

  # Test initial state values
  assert mapped_cover._target_position is None
  assert mapped_cover._target_tilt is None
  assert mapped_cover._last_position_command == 0
  assert mapped_cover._running_tasks == set()
  assert mapped_cover._state_listeners == []

  # Test event initialization
  assert mapped_cover._target_changed_event is not None
  assert not mapped_cover._target_changed_event.is_set()


@pytest.mark.asyncio
async def test_unique_id_generation(hass: HomeAssistant, full_mock_setup, cleanup_timers):
  """Test unique_id generation format: {entry_id}_{source_entity_id}."""
  setup_data = full_mock_setup
  config_entry = setup_data["config_entry"]
  throttler = MockThrottler()

  # Create the MappedCover entity
  mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", throttler)

  # Test unique_id format
  expected_unique_id = f"{config_entry.entry_id}_cover.test_cover"
  assert mapped_cover.unique_id == expected_unique_id


@pytest.mark.asyncio
async def test_device_info_creation(hass: HomeAssistant, full_mock_setup, cleanup_timers):
  """Test device_info creation with correct identifiers and metadata."""
  setup_data = full_mock_setup
  config_entry = setup_data["config_entry"]
  throttler = MockThrottler()

  # Create the MappedCover entity
  mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", throttler)

  # Test device_info structure
  device_info = mapped_cover.device_info

  assert device_info is not None
  assert "identifiers" in device_info
  assert "name" in device_info
  assert "manufacturer" in device_info
  assert "model" in device_info

  # Test device identifiers format
  expected_identifiers = {(DOMAIN, mapped_cover.unique_id)}
  assert device_info["identifiers"] == expected_identifiers

  # Test device metadata
  assert device_info["name"] == mapped_cover.name
  assert device_info["manufacturer"] == "Mapped Cover Integration"
  assert device_info["model"] == "Virtual Cover"


@pytest.mark.asyncio
async def test_name_generation_with_device(hass: HomeAssistant, cleanup_timers):
  """Test name generation using regex patterns when device exists."""
  # Create a config entry with custom rename pattern
  config_entry = await create_mock_config_entry(
    hass,
    entry_id="test_entry",
    covers=["cover.bedroom_blinds"],
    rename_pattern=r"^(.*)$",
    rename_replacement=r"Smart \1"
  )

  # Create mock registries with a device
  dev_reg = get_device_registry(hass)
  ent_reg = get_entity_registry(hass)

  # Create a device
  device = dev_reg.async_get_or_create(
    config_entry_id=config_entry.entry_id,
    identifiers={("test", "bedroom_device")},
    name="Bedroom Blinds Device"
  )

  # Create entity registry entry linking to the device
  ent_reg.async_get_or_create(
    "cover",
    "test",
    "bedroom_blinds",
    suggested_object_id="bedroom_blinds",
    device_id=device.id,
    original_name="Bedroom Blinds"
  )

  # Create the cover state
  await create_mock_cover_entity(hass, "cover.bedroom_blinds")

  throttler = MockThrottler()
  mapped_cover = MappedCover(hass, config_entry, "cover.bedroom_blinds", throttler)

  # Test name generation with device name
  assert mapped_cover.name == "Smart Bedroom Blinds Device"


@pytest.mark.asyncio
async def test_name_generation_without_device(hass: HomeAssistant, cleanup_timers):
  """Test name generation using entity_id when no device exists."""
  # Create a config entry with custom rename pattern
  config_entry = await create_mock_config_entry(
    hass,
    entry_id="test_entry",
    covers=["cover.living_room_curtains"],
    rename_pattern=r"cover\.(.*)_curtains",
    rename_replacement=r"Mapped \1 Curtains"
  )

  # Create the cover state without device association
  await create_mock_cover_entity(hass, "cover.living_room_curtains")

  throttler = MockThrottler()
  mapped_cover = MappedCover(hass, config_entry, "cover.living_room_curtains", throttler)

  # Test name generation with entity_id when no device
  assert mapped_cover.name == "Mapped living_room Curtains"


@pytest.mark.asyncio
async def test_entity_availability_available(hass: HomeAssistant, full_mock_setup, cleanup_timers):
  """Test entity availability when underlying cover is available."""
  setup_data = full_mock_setup
  config_entry = setup_data["config_entry"]

  # Create the cover state as available
  hass.states.async_set(
    "cover.test_cover",
    "closed",
    {"supported_features": 143, "current_position": 0}
  )

  throttler = MockThrottler()
  mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", throttler)

  # Test availability when source is available
  assert mapped_cover.available is True


@pytest.mark.asyncio
async def test_entity_availability_unavailable(hass: HomeAssistant, full_mock_setup, cleanup_timers):
  """Test entity availability when underlying cover is unavailable."""
  setup_data = full_mock_setup
  config_entry = setup_data["config_entry"]

  # Create the cover state as unavailable
  hass.states.async_set("cover.test_cover", "unavailable")

  throttler = MockThrottler()
  mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", throttler)

  # Test availability when source is unavailable
  assert mapped_cover.available is False


@pytest.mark.asyncio
async def test_entity_availability_unknown(hass: HomeAssistant, full_mock_setup, cleanup_timers):
  """Test entity availability when underlying cover state is unknown."""
  setup_data = full_mock_setup
  config_entry = setup_data["config_entry"]

  # Create the cover state as unknown
  hass.states.async_set("cover.test_cover", "unknown")

  throttler = MockThrottler()
  mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", throttler)

  # Test availability when source is unknown
  assert mapped_cover.available is False


@pytest.mark.asyncio
async def test_entity_availability_missing(hass: HomeAssistant, full_mock_setup, cleanup_timers):
  """Test entity availability when underlying cover doesn't exist."""
  setup_data = full_mock_setup
  config_entry = setup_data["config_entry"]

  # Don't create any cover state

  throttler = MockThrottler()
  mapped_cover = MappedCover(hass, config_entry, "cover.nonexistent_cover", throttler)

  # Test availability when source doesn't exist
  assert mapped_cover.available is False


@pytest.mark.asyncio
async def test_config_properties_access(hass: HomeAssistant, cleanup_timers):
  """Test access to configuration properties from config entry."""
  # Create a config entry with specific values
  config_entry = await create_mock_config_entry(
    hass,
    entry_id="test_entry",
    covers=["cover.test_cover"],
    rename_pattern=r"^Test (.*)$",
    rename_replacement=r"Mapped \1",
    min_position=15,
    max_position=85,
    min_tilt_position=10,
    max_tilt_position=90,
    close_tilt_if_down=False,
    throttle=200
  )

  await create_mock_cover_entity(hass, "cover.test_cover")

  throttler = MockThrottler()
  mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", throttler)

  # Test all configuration property accessors
  assert mapped_cover._rename_pattern == r"^Test (.*)$"
  assert mapped_cover._rename_replacement == r"Mapped \1"
  assert mapped_cover._min_pos == 15
  assert mapped_cover._max_pos == 85
  assert mapped_cover._min_tilt == 10
  assert mapped_cover._max_tilt == 90
  assert mapped_cover._close_tilt_if_down is False


@pytest.mark.asyncio
async def test_device_registry_lookup(hass: HomeAssistant, cleanup_timers):
  """Test device registry lookup during initialization."""
  config_entry = await create_mock_config_entry(
    hass,
    entry_id="test_entry",
    covers=["cover.test_cover"]
  )

  # Create registries and device
  dev_reg = get_device_registry(hass)
  ent_reg = get_entity_registry(hass)

  # Create a device
  device = dev_reg.async_get_or_create(
    config_entry_id=config_entry.entry_id,
    identifiers={("test", "test_device")},
    name="Test Device"
  )

  # Create entity registry entry with device association
  ent_reg.async_get_or_create(
    "cover",
    "test",
    "test_cover",
    suggested_object_id="test_cover",
    device_id=device.id,
    original_name="Test Cover"
  )

  await create_mock_cover_entity(hass, "cover.test_cover")

  throttler = MockThrottler()
  mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", throttler)

  # Test device was found and stored
  assert mapped_cover._device is not None
  assert mapped_cover._device.id == device.id
  assert mapped_cover._device.name == "Test Device"


@pytest.mark.asyncio
async def test_device_registry_lookup_no_device(hass: HomeAssistant, cleanup_timers):
  """Test device registry lookup when entity has no device."""
  config_entry = await create_mock_config_entry(
    hass,
    entry_id="test_entry",
    covers=["cover.test_cover"]
  )

  # Create entity registry entry without device association
  ent_reg = get_entity_registry(hass)
  ent_reg.async_get_or_create(
    "cover",
    "test",
    "test_cover",
    suggested_object_id="test_cover",
    device_id=None,  # No device
    original_name="Test Cover"
  )

  await create_mock_cover_entity(hass, "cover.test_cover")

  throttler = MockThrottler()
  mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", throttler)

  # Test device is None when entity has no device
  assert mapped_cover._device is None


@pytest.mark.asyncio
async def test_device_registry_lookup_entity_not_registered(hass: HomeAssistant, cleanup_timers):
  """Test device registry lookup when entity is not registered."""
  config_entry = await create_mock_config_entry(
    hass,
    entry_id="test_entry",
    covers=["cover.test_cover"]
  )

  # Don't create any entity registry entry
  await create_mock_cover_entity(hass, "cover.test_cover")

  throttler = MockThrottler()
  mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", throttler)

  # Test device is None when entity is not registered
  assert mapped_cover._device is None
