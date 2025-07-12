"""Test entity creation and initialization for MappedCover."""
import pytest
import pytest_check as check
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as get_entity_registry
from homeassistant.helpers.device_registry import async_get as get_device_registry
from custom_components.mappedcover.cover import MappedCover
from custom_components.mappedcover.const import DOMAIN

# Import from helpers instead of original helpers
from tests.helpers import create_mock_config_entry, create_mock_cover_entity, MockThrottler
from tests.fixtures import *  # Import all shared fixtures


@pytest.mark.asyncio
async def test_mapped_cover_init(hass: HomeAssistant, full_mock_setup):
    """Test MappedCover initialization with all required parameters."""
    config_entry = full_mock_setup["config_entry"]

    # Create a throttler for the test
    throttler = MockThrottler()

    # Create the MappedCover entity
    mapped_cover = MappedCover(
        hass, config_entry, "cover.test_cover", throttler)

    # Test basic initialization
    check.equal(mapped_cover.hass, hass)
    check.equal(mapped_cover._entry, config_entry)
    check.equal(mapped_cover._source_entity_id, "cover.test_cover")
    check.equal(mapped_cover._throttler, throttler)

    # Test initial state values
    check.is_none(mapped_cover._target_position)
    check.is_none(mapped_cover._target_tilt)
    check.equal(mapped_cover._last_position_command, 0)
    check.equal(mapped_cover._running_tasks, set())
    check.equal(mapped_cover._state_listeners, [])

    # Test event initialization
    check.is_true(mapped_cover._target_changed_event is not None)
    check.is_false(mapped_cover._target_changed_event.is_set())


@pytest.mark.asyncio
async def test_unique_id_generation(hass: HomeAssistant, full_mock_setup):
    """Test unique_id generation format: {entry_id}_{source_entity_id}."""
    config_entry = full_mock_setup["config_entry"]
    throttler = MockThrottler()

    # Create the MappedCover entity
    mapped_cover = MappedCover(
        hass, config_entry, "cover.test_cover", throttler)

    # Test unique_id format
    expected_unique_id = f"{config_entry.entry_id}_cover.test_cover"
    check.equal(mapped_cover.unique_id, expected_unique_id)


@pytest.mark.asyncio
async def test_device_info_creation(hass: HomeAssistant, full_mock_setup):
    """Test device_info creation with correct identifiers and metadata."""
    config_entry = full_mock_setup["config_entry"]
    throttler = MockThrottler()

    mapped_cover = MappedCover(
        hass, config_entry, "cover.test_cover", throttler)
    device_info = mapped_cover.device_info

    check.is_not_none(device_info)
    check.is_in("identifiers", device_info)
    check.is_in("name", device_info)
    check.is_in("manufacturer", device_info)
    check.is_in("model", device_info)

    expected_identifiers = {(DOMAIN, mapped_cover.unique_id)}
    check.equal(device_info["identifiers"], expected_identifiers)
    check.equal(device_info["name"], mapped_cover.name)
    check.equal(device_info["manufacturer"], "Mapped Cover Integration")
    check.equal(device_info["model"], "Virtual Cover")


@pytest.mark.asyncio
async def test_name_generation_with_device(hass: HomeAssistant):
    """Test name generation using regex patterns when device exists."""
    config_entry = await create_mock_config_entry(
        hass,
        entry_id="test_entry",
        covers=["cover.bedroom_blinds"],
        rename_pattern=r"^(.*)$",
        rename_replacement=r"Smart \1"  # FIXED: use raw string, single backslash
    )
    dev_reg = get_device_registry(hass)
    ent_reg = get_entity_registry(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("test", "bedroom_device")},
        name="Bedroom Blinds Device"
    )
    ent_reg.async_get_or_create(
        "cover",
        "test",
        "bedroom_blinds",
        suggested_object_id="bedroom_blinds",
        device_id=device.id,
        original_name="Bedroom Blinds"
    )
    create_mock_cover_entity(hass, "cover.bedroom_blinds")
    throttler = MockThrottler()
    mapped_cover = MappedCover(
        hass, config_entry, "cover.bedroom_blinds", throttler)
    check.equal(mapped_cover.name, "Smart Bedroom Blinds Device")


@pytest.mark.asyncio
async def test_name_generation_without_device(hass: HomeAssistant):
    """Test name generation using entity_id when no device exists."""
    config_entry = await create_mock_config_entry(
        hass,
        entry_id="test_entry",
        covers=["cover.living_room_curtains"],
        rename_pattern=r"cover\.(.*)_curtains",
        # FIXED: use raw string, single backslash
        rename_replacement=r"Mapped \1 Curtains"
    )
    create_mock_cover_entity(hass, "cover.living_room_curtains")
    throttler = MockThrottler()
    mapped_cover = MappedCover(
        hass, config_entry, "cover.living_room_curtains", throttler)
    check.equal(mapped_cover.name, "Mapped living_room Curtains")


@pytest.mark.asyncio
async def test_entity_availability_available(hass: HomeAssistant, full_mock_setup):
    """Test entity availability when underlying cover is available."""
    config_entry = full_mock_setup["config_entry"]
    hass.states.async_set(
        "cover.test_cover",
        "closed",
        {"supported_features": 143, "current_position": 0}
    )
    throttler = MockThrottler()
    mapped_cover = MappedCover(
        hass, config_entry, "cover.test_cover", throttler)
    check.is_true(mapped_cover.available)


@pytest.mark.asyncio
async def test_entity_availability_unavailable(hass: HomeAssistant, full_mock_setup):
    """Test entity availability when underlying cover is unavailable."""
    config_entry = full_mock_setup["config_entry"]
    hass.states.async_set("cover.test_cover", "unavailable")
    throttler = MockThrottler()
    mapped_cover = MappedCover(
        hass, config_entry, "cover.test_cover", throttler)
    check.is_false(mapped_cover.available)


@pytest.mark.asyncio
async def test_entity_availability_unknown(hass: HomeAssistant, full_mock_setup):
    """Test entity availability when underlying cover state is unknown."""
    config_entry = full_mock_setup["config_entry"]
    hass.states.async_set("cover.test_cover", "unknown")
    throttler = MockThrottler()
    mapped_cover = MappedCover(
        hass, config_entry, "cover.test_cover", throttler)
    check.is_false(mapped_cover.available)


@pytest.mark.asyncio
async def test_entity_availability_missing(hass: HomeAssistant, full_mock_setup):
    """Test entity availability when underlying cover doesn't exist."""
    config_entry = full_mock_setup["config_entry"]
    throttler = MockThrottler()
    mapped_cover = MappedCover(
        hass, config_entry, "cover.nonexistent_cover", throttler)
    check.is_false(mapped_cover.available)


@pytest.mark.asyncio
async def test_config_properties_access(hass: HomeAssistant):
    """Test access to configuration properties from config entry."""
    config_entry = await create_mock_config_entry(
        hass,
        entry_id="test_entry",
        covers=["cover.test_cover"],
        rename_pattern=r"^Test (.*)$",
        rename_replacement=r"Mapped \\1",
        min_position=15,
        max_position=85,
        min_tilt_position=10,
        max_tilt_position=90,
        close_tilt_if_down=False,
        throttle=200
    )
    create_mock_cover_entity(hass, "cover.test_cover")
    throttler = MockThrottler()
    mapped_cover = MappedCover(
        hass, config_entry, "cover.test_cover", throttler)
    check.equal(mapped_cover._rename_pattern, r"^Test (.*)$")
    check.equal(mapped_cover._rename_replacement, r"Mapped \\1")
    check.equal(mapped_cover._min_pos, 15)
    check.equal(mapped_cover._max_pos, 85)
    check.equal(mapped_cover._min_tilt, 10)
    check.equal(mapped_cover._max_tilt, 90)
    check.is_false(mapped_cover._close_tilt_if_down)


@pytest.mark.asyncio
async def test_device_registry_lookup(hass: HomeAssistant):
    """Test device registry lookup during initialization."""
    config_entry = await create_mock_config_entry(
        hass,
        entry_id="test_entry",
        covers=["cover.test_cover"]
    )
    dev_reg = get_device_registry(hass)
    ent_reg = get_entity_registry(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("test", "test_device")},
        name="Test Device"
    )
    ent_reg.async_get_or_create(
        "cover",
        "test",
        "test_cover",
        suggested_object_id="test_cover",
        device_id=device.id,
        original_name="Test Cover"
    )
    create_mock_cover_entity(hass, "cover.test_cover")
    throttler = MockThrottler()
    mapped_cover = MappedCover(
        hass, config_entry, "cover.test_cover", throttler)
    check.is_not_none(mapped_cover._device)
    check.equal(mapped_cover._device.id, device.id)
    check.equal(mapped_cover._device.name, "Test Device")


@pytest.mark.asyncio
async def test_device_registry_lookup_no_device(hass: HomeAssistant):
    """Test device registry lookup when entity has no device."""
    config_entry = await create_mock_config_entry(
        hass,
        entry_id="test_entry",
        covers=["cover.test_cover"]
    )
    ent_reg = get_entity_registry(hass)
    ent_reg.async_get_or_create(
        "cover",
        "test",
        "test_cover",
        suggested_object_id="test_cover",
        device_id=None,
        original_name="Test Cover"
    )
    create_mock_cover_entity(hass, "cover.test_cover")
    throttler = MockThrottler()
    mapped_cover = MappedCover(
        hass, config_entry, "cover.test_cover", throttler)
    check.is_none(mapped_cover._device)


@pytest.mark.asyncio
async def test_device_registry_lookup_entity_not_registered(hass: HomeAssistant):
    """Test device registry lookup when entity is not registered."""
    config_entry = await create_mock_config_entry(
        hass,
        entry_id="test_entry",
        covers=["cover.test_cover"]
    )
    create_mock_cover_entity(hass, "cover.test_cover")
    throttler = MockThrottler()
    mapped_cover = MappedCover(
        hass, config_entry, "cover.test_cover", throttler)
    check.is_none(mapped_cover._device)
