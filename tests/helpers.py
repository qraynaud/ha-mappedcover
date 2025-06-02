"""Shared test helpers for mappedcover tests."""
import asyncio
from unittest.mock import MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_registry import async_get as get_entity_registry
from homeassistant.helpers.device_registry import async_get as get_device_registry
from homeassistant.helpers.area_registry import async_get as get_area_registry
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from custom_components.mappedcover.const import DOMAIN


class MockThrottler:
    """Mock Throttler class for testing."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        pass


async def cleanup_platform_timers(hass: HomeAssistant):
    """Clean up any lingering platform timers to avoid test warnings."""
    all_platforms = hass.data.get("entity_platform", {})

    for domain, platforms in all_platforms.items():
        for platform in platforms:
            if hasattr(platform, '_async_polling_timer') and platform._async_polling_timer:
                platform._async_polling_timer.cancel()
                platform._async_polling_timer = None


async def create_mock_cover_entity(
    hass: HomeAssistant,
    entity_id: str,
    state: str = "closed",
    supported_features: int = 143,
    current_position: int = 0,
    current_tilt_position: int = 0,
    device_class: str = "blind"
):
    """Create a mock cover entity with standard attributes."""
    hass.states.async_set(
        entity_id,
        state,
        {
            "supported_features": supported_features,
            "current_position": current_position,
            "current_tilt_position": current_tilt_position,
            "device_class": device_class
        }
    )


async def create_mock_config_entry(
    hass: HomeAssistant,
    entry_id: str = "test_entry_id",
    title: str = "Test Mapped Cover",
    covers: list = None,
    rename_pattern: str = "^(.*)$",
    rename_replacement: str = "Mapped \\1",
    min_position: int = 10,
    max_position: int = 90,
    min_tilt_position: int = 5,
    max_tilt_position: int = 95,
    close_tilt_if_down: bool = True,
    throttle: int = 150
) -> ConfigEntry:
    """Create a mock config entry with standard test data."""
    if covers is None:
        covers = ["cover.test_cover"]

    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title=title,
        data={
            "covers": covers,
            "rename_pattern": rename_pattern,
            "rename_replacement": rename_replacement,
            "min_position": min_position,
            "max_position": max_position,
            "min_tilt_position": min_tilt_position,
            "max_tilt_position": max_tilt_position,
            "close_tilt_if_down": close_tilt_if_down,
            "throttle": throttle,
        },
        source="user",
        options={},
        unique_id=entry_id,
        minor_version=1,
        discovery_keys=[],
        subentries_data={}
    )

    await hass.config_entries.async_add(entry)
    return entry


async def setup_mock_registries(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    area_name: str = "test_area",
    device_name: str = "Test Source Device",
    entity_name: str = "Test Cover",
    source_entity_id: str = "cover.test_cover"
):
    """Set up mock area, device, and entity registries."""
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
        COVER_DOMAIN,
        "test",
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


async def setup_platform_with_entities(hass: HomeAssistant, config_entry: ConfigEntry):
    """Helper to setup platform and return added entities."""
    from unittest.mock import patch
    from custom_components.mappedcover.cover import async_setup_entry

    added_entities = []

    async def mock_add_entities(entities, update_before_add=False):
        added_entities.extend(entities)

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        await async_setup_entry(hass, config_entry, mock_add_entities)

    return added_entities


async def create_config_flow_entry(
    hass: HomeAssistant,
    label: str = "Test Mapped Cover",
    covers: list = None,
    rename_pattern: str = "^(.*)$",
    rename_replacement: str = "Mapped \\1",
    min_position: int = 10,
    max_position: int = 90,
    min_tilt_position: int = 5,
    max_tilt_position: int = 95,
    close_tilt_if_down: bool = True,
    throttle: int = 150
) -> ConfigEntry:
    """Create a config entry through the normal config flow."""
    from homeassistant.setup import async_setup_component

    if covers is None:
        covers = ["cover.real_mappedcover"]

    await async_setup_component(hass, DOMAIN, {})

    # Create an entry using the config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    # Complete first step
    user_input_step1 = {
        "label": label,
        "covers": covers,
    }
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=user_input_step1
    )

    # Complete second step
    user_input_step2 = {
        "rename_pattern": rename_pattern,
        "rename_replacement": rename_replacement,
        "min_position": min_position,
        "max_position": max_position,
        "close_tilt_if_down": close_tilt_if_down,
        "throttle": throttle,
    }

    # Only add tilt fields if the schema supports them
    schema_str = str(result2["data_schema"]).lower()
    if "min_tilt_position" in schema_str:
        user_input_step2.update({
            "min_tilt_position": min_tilt_position,
            "max_tilt_position": max_tilt_position,
        })

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], user_input=user_input_step2
    )

    # Get the created entry
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    return entry


def create_standard_mock_covers(hass: HomeAssistant):
    """Create standard mock cover entities used across tests."""
    # Feature 15 = OPEN+CLOSE+SET_POSITION+STOP (1+2+4+8)
    # Feature 143 = 15 + OPEN_TILT+SET_TILT_POSITION (15+16+128)
    hass.states.async_set(
        "cover.real_mappedcover",
        "closed",
        {"supported_features": 143, "device_class": "mappedcover"}
    )
    hass.states.async_set(
        "cover.another_mappedcover",
        "open",
        {"supported_features": 143, "device_class": "blind"}
    )
    hass.states.async_set(
        "cover.mapped_mappedcover_1",
        "closed",
        {"supported_features": 143, "device_class": "mappedcover"}
    )


async def assert_config_flow_step(result, step_id: str, expected_fields: list = None):
    """Assert config flow step properties and optionally check for expected fields."""
    assert result["type"] == "form"
    assert result["step_id"] == step_id
    assert result["data_schema"] is not None

    if expected_fields:
        schema_str = str(result["data_schema"]).lower()
        for field in expected_fields:
            assert field.lower() in schema_str, f"Expected field '{field}' not found in schema"


async def complete_config_flow_step(hass: HomeAssistant, flow_id: str, user_input: dict):
    """Complete a config flow step and return the result."""
    return await hass.config_entries.flow.async_configure(flow_id, user_input=user_input)


async def assert_config_entry_created(result, expected_title: str, expected_data: dict = None):
    """Assert that a config entry was created with expected properties."""
    assert result["type"] == "create_entry"
    assert result["title"] == expected_title

    if expected_data:
        data = result["data"]
        for key, value in expected_data.items():
            assert data[key] == value, f"Expected {key}={value}, got {data[key]}"


# Test constants
TEST_ENTRY_ID = "test_entry_id"
TEST_COVER_ID = "cover.test_cover"
TEST_AREA_ID = "test_area"
TEST_DEVICE_NAME = "Test Source Device"
TEST_ENTITY_NAME = "Test Cover"

# Standard cover features
FEATURES_BASIC = 15  # OPEN+CLOSE+SET_POSITION+STOP
FEATURES_WITH_TILT = 143  # FEATURES_BASIC + OPEN_TILT+SET_TILT_POSITION

# Common test data
STANDARD_CONFIG_DATA = {
    "rename_pattern": "^(.*)$",
    "rename_replacement": "Mapped \\1",
    "min_position": 10,
    "max_position": 90,
    "min_tilt_position": 5,
    "max_tilt_position": 95,
    "close_tilt_if_down": True,
    "throttle": 150,
}

# Convergence test helpers
from unittest.mock import patch, AsyncMock, PropertyMock, ANY
from custom_components.mappedcover.cover import MappedCover


def create_convergence_test_setup(
    hass,
    mock_config_entry,
    entity_id: str = "cover.test_cover",
    state: str = "open",
    current_position: int = 30,
    current_tilt_position: int = 40,
    target_position: int = None,
    target_tilt: int = None,
    is_moving: bool = False,
    last_position_command_time: float = None
):
    """Create a standard setup for convergence tests with a MappedCover entity.

    Returns:
        tuple: (mapped_cover, call_tracker) where call_tracker is a list that tracks service calls
    """
    hass.states.async_set(
        entity_id,
        state,
        {
            "supported_features": 143,
            "current_position": current_position,
            "current_tilt_position": current_tilt_position,
            "device_class": "blind"
        }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        mapped_cover = MappedCover(hass, mock_config_entry, entity_id, MockThrottler())

    # Set targets
    mapped_cover._target_position = target_position
    mapped_cover._target_tilt = target_tilt

    # Set moving state if needed
    if last_position_command_time is not None:
        mapped_cover._last_position_command = last_position_command_time
    elif not is_moving:
        mapped_cover._last_position_command = None

    # Call tracker for service calls
    call_tracker = []

    return mapped_cover, call_tracker


def create_convergence_state_simulator(hass, entity_id: str = "cover.test_cover"):
    """Create a state simulator that updates cover state after service calls.

    Returns:
        function: async function that can be used as side_effect for _call_service mock
    """
    async def simulate_state_changes(service_name, service_data=None, **kwargs):
        current_state = hass.states.get(entity_id)
        if not current_state:
            return

        current_attrs = dict(current_state.attributes)

        if service_name == "set_cover_position" and service_data:
            current_attrs["current_position"] = service_data.get("position", current_attrs.get("current_position"))
        elif service_name == "set_cover_tilt_position" and service_data:
            current_attrs["current_tilt_position"] = service_data.get("tilt_position", current_attrs.get("current_tilt_position"))

        hass.states.async_set(entity_id, current_state.state, current_attrs)

    return simulate_state_changes


class ConvergenceTestContext:
    """Context manager for convergence tests that handles common mocking patterns."""

    def __init__(
        self,
        mapped_cover,
        call_tracker: list,
        is_moving: bool = False,
        wait_for_attribute_return: bool = True,
        simulate_state_changes: bool = True,
        hass=None,
        entity_id: str = "cover.test_cover"
    ):
        self.mapped_cover = mapped_cover
        self.call_tracker = call_tracker
        self.is_moving = is_moving
        self.wait_for_attribute_return = wait_for_attribute_return
        self.simulate_state_changes = simulate_state_changes
        self.hass = hass
        self.entity_id = entity_id
        self._patches = []

    async def track_calls(self, service_name, service_data=None, **kwargs):
        """Track service calls and optionally simulate state changes."""
        self.call_tracker.append(service_name)

        if self.simulate_state_changes and self.hass:
            await create_convergence_state_simulator(self.hass, self.entity_id)(
                service_name, service_data, **kwargs
            )

    def __enter__(self):
        # Patch _call_service with call tracking
        call_service_patch = patch.object(
            self.mapped_cover, '_call_service',
            side_effect=self.track_calls
        )
        self._patches.append(call_service_patch)

        # Patch async_write_ha_state
        write_state_patch = patch.object(self.mapped_cover, 'async_write_ha_state')
        self._patches.append(write_state_patch)

        # Patch _wait_for_attribute
        wait_attr_patch = patch.object(
            self.mapped_cover, '_wait_for_attribute',
            return_value=self.wait_for_attribute_return
        )
        self._patches.append(wait_attr_patch)

        # Patch is_moving property
        is_moving_patch = patch.object(
            type(self.mapped_cover), 'is_moving',
            new_callable=PropertyMock,
            return_value=self.is_moving
        )
        self._patches.append(is_moving_patch)

        # Start all patches
        for p in self._patches:
            p.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Stop all patches
        for p in self._patches:
            p.stop()

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.__exit__(exc_type, exc_val, exc_tb)


def assert_service_call_order(call_tracker: list, expected_calls: list):
    """Assert that service calls happened in the expected order."""
    assert len(call_tracker) == len(expected_calls), \
        f"Expected {len(expected_calls)} calls, got {len(call_tracker)}: {call_tracker}"

    for i, expected_call in enumerate(expected_calls):
        assert call_tracker[i] == expected_call, \
            f"Call {i}: expected '{expected_call}', got '{call_tracker[i]}'"


def assert_service_not_called(call_tracker: list, service_name: str):
    """Assert that a specific service was not called."""
    assert service_name not in call_tracker, \
        f"Service '{service_name}' should not have been called, but found in: {call_tracker}"


def assert_service_called(call_tracker: list, service_name: str):
    """Assert that a specific service was called."""
    assert service_name in call_tracker, \
        f"Service '{service_name}' should have been called, but not found in: {call_tracker}"


async def create_convergence_test_cover(
    hass,
    mock_config_entry,
    entity_id: str = "cover.test_cover",
    **state_attrs
) -> MappedCover:
    """Create a MappedCover for convergence testing with default attributes."""
    default_attrs = {
        "state": "open",
        "supported_features": 143,
        "current_position": 30,
        "current_tilt_position": 40,
        "device_class": "blind"
    }
    default_attrs.update(state_attrs)

    state = default_attrs.pop("state")

    hass.states.async_set(entity_id, state, default_attrs)

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        return MappedCover(hass, mock_config_entry, entity_id, MockThrottler())


# Common convergence test scenarios

async def run_tilt_first_test(
    hass,
    mock_config_entry,
    target_position: int = 70,
    target_tilt: int = 80,
    current_position: int = 30,
    current_tilt_position: int = 40,
    is_moving: bool = False,
    wait_for_attribute_return: bool = True
):
    """Run a tilt-first logic test scenario and return the call tracker."""
    mapped_cover, call_tracker = create_convergence_test_setup(
        hass, mock_config_entry,
        current_position=current_position,
        current_tilt_position=current_tilt_position,
        target_position=target_position,
        target_tilt=target_tilt,
        is_moving=is_moving
    )

    async with ConvergenceTestContext(
        mapped_cover, call_tracker,
        is_moving=is_moving,
        wait_for_attribute_return=wait_for_attribute_return,
        hass=hass
    ):
        await mapped_cover.converge_position()

    return call_tracker


async def run_stop_if_moving_test(
    hass,
    mock_config_entry,
    target_position: int = 70,
    current_position: int = 70,
    is_moving: bool = True,
    should_stop: bool = True
):
    """Run a stop-if-moving test scenario and return the call tracker."""
    mapped_cover, call_tracker = create_convergence_test_setup(
        hass, mock_config_entry,
        state="opening" if is_moving else "open",
        current_position=current_position,
        target_position=target_position,
        is_moving=is_moving
    )

    # For stop scenarios, we need to patch asyncio.sleep too
    async def track_calls_with_stop(service_name, service_data=None, **kwargs):
        call_tracker.append(service_name)

    with patch.object(mapped_cover, '_call_service', side_effect=track_calls_with_stop), \
         patch.object(mapped_cover, 'async_write_ha_state'), \
         patch.object(mapped_cover, '_wait_for_attribute', new_callable=AsyncMock), \
         patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=is_moving), \
         patch('asyncio.sleep', new_callable=AsyncMock):
        await mapped_cover.converge_position()

    return call_tracker


async def run_position_convergence_test(
    hass,
    mock_config_entry,
    current_position: int = 30,
    target_position: int = 70,
    current_tilt_position: int = 40,
    target_tilt: int = None,
    expect_position_call: bool = True
):
    """Run a test for basic position convergence with retry mechanism.

    Returns:
        tuple: (call_tracker, mock_call_service) for asserting more specific behaviors
    """
    hass.states.async_set(
        "cover.test_cover",
        "open",
        {
            "supported_features": 143,
            "current_position": current_position,
            "current_tilt_position": current_tilt_position,
            "device_class": "blind"
        }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    mapped_cover._target_position = target_position
    mapped_cover._target_tilt = target_tilt

    call_tracker = []
    mock_call_service = AsyncMock(side_effect=lambda *args, **kwargs: call_tracker.append(args[0]))

    with patch.object(mapped_cover, '_call_service', mock_call_service), \
         patch.object(mapped_cover, 'async_write_ha_state'):
        await mapped_cover.converge_position()

    # Verify expected behavior
    if expect_position_call:
        assert "set_cover_position" in call_tracker
    else:
        assert "set_cover_position" not in call_tracker

    return call_tracker, mock_call_service


async def run_tilt_convergence_test(
    hass,
    mock_config_entry,
    current_tilt_position: int = 30,
    target_tilt: int = 80,
    current_position: int = 50,
    target_position: int = None,
    expect_tilt_call: bool = True
):
    """Run a test for basic tilt convergence with retry mechanism.

    Returns:
        tuple: (call_tracker, mock_call_service) for asserting more specific behaviors
    """
    hass.states.async_set(
        "cover.test_cover",
        "open",
        {
            "supported_features": 143,
            "current_position": current_position,
            "current_tilt_position": current_tilt_position,
            "device_class": "blind"
        }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    mapped_cover._target_position = target_position
    mapped_cover._target_tilt = target_tilt

    call_tracker = []
    mock_call_service = AsyncMock(side_effect=lambda *args, **kwargs: call_tracker.append(args[0]))

    with patch.object(mapped_cover, '_call_service', mock_call_service), \
         patch.object(mapped_cover, 'async_write_ha_state'):
        await mapped_cover.converge_position()

    # Verify expected behavior
    if expect_tilt_call:
        assert "set_cover_tilt_position" in call_tracker
    else:
        assert "set_cover_tilt_position" not in call_tracker

    return call_tracker, mock_call_service


async def run_close_tilt_if_down_test(
    hass,
    mock_config_entry,
    current_tilt_position: int = 80,
    target_tilt: int = 40,
    feature_enabled: bool = True,
    tilt_decreasing: bool = True,
    with_position_target: bool = False
):
    """Run a test for close_tilt_if_down special behavior.

    Args:
        hass: Home assistant instance
        mock_config_entry: Config entry fixture
        current_tilt_position: Current tilt position (defaults to 80)
        target_tilt: Target tilt position (defaults to 40)
        feature_enabled: Whether close_tilt_if_down is enabled in config
        tilt_decreasing: If True, tilt target is lower than current
        with_position_target: If True, also sets a position target

    Returns:
        list: List of (service_name, tilt_position) tuples
    """
    # Adjust tilt values if needed for the "increasing" case
    if not tilt_decreasing:
        current_tilt_position, target_tilt = 30, 70

    hass.states.async_set(
        "cover.test_cover",
        "open",
        {
            "supported_features": 143,
            "current_position": 50,
            "current_tilt_position": current_tilt_position,
            "device_class": "blind"
        }
    )

    # Create cover entity with proper mocking of the wait_for_attribute method
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler), \
         patch("custom_components.mappedcover.cover.MappedCover._wait_for_attribute", return_value=True):
        mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set targets according to test parameters
    mapped_cover._target_position = 60 if with_position_target else None
    mapped_cover._target_tilt = target_tilt

    # Store original event for cleanup
    original_event = mapped_cover._target_changed_event
    # Mock the event to prevent lingering tasks
    mapped_cover._target_changed_event = MagicMock()
    mapped_cover._target_changed_event.set = MagicMock()
    mapped_cover._target_changed_event.wait = AsyncMock()

    call_order = []

    try:
        # Track service calls to record the order and parameters
        async def track_calls(service_name, service_data, **kwargs):
            tilt_pos = service_data.get("tilt_position", service_data.get("position"))
            call_order.append((service_name, tilt_pos))

        # Apply all necessary patches with proper context management
        with patch.object(type(mapped_cover), '_close_tilt_if_down',
                         new_callable=PropertyMock, return_value=feature_enabled), \
             patch.object(mapped_cover, '_call_service', side_effect=track_calls), \
             patch.object(mapped_cover, 'async_write_ha_state'), \
             patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):

            # Run the convergence logic
            await mapped_cover.converge_position()

        # Return call order for assertions
        return call_order
    finally:
        # Restore the original event to ensure proper cleanup
        mapped_cover._target_changed_event = original_event

    # Return call order for more specific assertions
    return call_order


async def run_abort_logic_test(
    hass,
    mock_config_entry,
    change_position_target: bool = True,
    change_tilt_target: bool = False,
    call_to_change_at: int = 1
):
    """Run a test for abort logic when targets change during execution.

    Args:
        hass: Home assistant instance
        mock_config_entry: Config entry fixture
        change_position_target: Whether to change position target during execution
        change_tilt_target: Whether to change tilt target during execution
        call_to_change_at: Which call number to change the target at

    Returns:
        tuple: (call_count, mapped_cover) for asserting abort behavior
    """
    hass.states.async_set(
        "cover.test_cover",
        "open",
        {
            "supported_features": 143,
            "current_position": 30,
            "current_tilt_position": 40,
            "device_class": "blind"
        }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set initial targets
    mapped_cover._target_position = 70
    mapped_cover._target_tilt = 80

    call_count = 0

    async def change_target_during_execution(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == call_to_change_at:
            if change_position_target:
                mapped_cover._target_position = 50
            if change_tilt_target:
                mapped_cover._target_tilt = 90

    with patch.object(mapped_cover, '_call_service', side_effect=change_target_during_execution), \
         patch.object(mapped_cover, 'async_write_ha_state'), \
         patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):
        await mapped_cover.converge_position()

    return call_count, mapped_cover


async def run_target_cleanup_test(
    hass,
    mock_config_entry,
    set_position_target: bool = True,
    set_tilt_target: bool = True,
    abort_during_execution: bool = False
):
    """Run a test for target cleanup after convergence completion.

    Args:
        hass: Home assistant instance
        mock_config_entry: Config entry fixture
        set_position_target: Whether to set a position target
        set_tilt_target: Whether to set a tilt target
        abort_during_execution: Whether to abort execution

    Returns:
        tuple: (mapped_cover, mock_write_state) for asserting cleanup behavior
    """
    hass.states.async_set(
        "cover.test_cover",
        "open",
        {
            "supported_features": 143,
            "current_position": 30,
            "current_tilt_position": 40,
            "device_class": "blind"
        }
    )

    # Create the cover entity with proper mocking
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler), \
         patch("custom_components.mappedcover.cover.MappedCover._wait_for_attribute", return_value=True):
        mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set specified targets
    mapped_cover._target_position = 70 if set_position_target else None
    mapped_cover._target_tilt = 80 if set_tilt_target else None

    # Create side effect to abort if needed
    if abort_during_execution:
        mock_call_service = AsyncMock(side_effect=lambda *args, **kwargs: setattr(mapped_cover, '_target_position', 50))
    else:
        mock_call_service = AsyncMock()

    mock_write_state = MagicMock()

    # Store original event for cleanup
    original_event = mapped_cover._target_changed_event
    # Mock the event to prevent lingering tasks
    mapped_cover._target_changed_event = MagicMock()
    mapped_cover._target_changed_event.set = MagicMock()
    mapped_cover._target_changed_event.wait = AsyncMock()

    try:
        # Apply all necessary patches in one context manager block
        with patch.object(mapped_cover, '_call_service', mock_call_service), \
             patch.object(mapped_cover, 'async_write_ha_state', mock_write_state), \
             patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):

            # Run the convergence logic
            await mapped_cover.converge_position()

        return mapped_cover, mock_write_state
    finally:
        # Restore the original event to ensure proper cleanup
        mapped_cover._target_changed_event = original_event


def create_tracked_cover(
    hass,
    mock_config_entry,
    entity_id: str = "cover.test_cover",
    state: str = "open",
    current_position: int = 30,
    current_tilt_position: int = 40,
    target_position: int = None,
    target_tilt: int = None
):
    """Create a MappedCover with call tracking for reuse across multiple tests.

    Returns:
        tuple: (mapped_cover, track_calls_fn, call_tracker)
    """
    hass.states.async_set(
        entity_id,
        state,
        {
            "supported_features": 143,
            "current_position": current_position,
            "current_tilt_position": current_tilt_position,
            "device_class": "blind"
        }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        mapped_cover = MappedCover(hass, mock_config_entry, entity_id, MockThrottler())

    # Set targets
    mapped_cover._target_position = target_position
    mapped_cover._target_tilt = target_tilt

    # Create tracking tools
    call_tracker = []

    async def track_calls(service_name, *args, **kwargs):
        call_tracker.append(service_name)
        # Simulate state changes after service calls
        if service_name == "set_cover_position" and args and "position" in args[0]:
            position = args[0]["position"]
            hass.states.async_set(
                entity_id,
                state,
                {
                    "supported_features": 143,
                    "current_position": position,
                    "current_tilt_position": current_tilt_position,
                    "device_class": "blind"
                }
            )
        elif service_name == "set_cover_tilt_position" and args and "tilt_position" in args[0]:
            tilt_position = args[0]["tilt_position"]
            hass.states.async_set(
                entity_id,
                state,
                {
                    "supported_features": 143,
                    "current_position": current_position,
                    "current_tilt_position": tilt_position,
                    "device_class": "blind"
                }
            )

    return mapped_cover, track_calls, call_tracker
