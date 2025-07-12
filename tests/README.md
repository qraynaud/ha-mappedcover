# Testing Guide for MappedCover Integration

This guide helps you write tests for the MappedCover Home Assistant integration. Our test infrastructure provides shared utilities, fixtures, and patterns to make testing easier and more consistent.

## Test Documentation

- **`README.md`** - This testing guide that covers how to write and run tests
- **`TEST_PLAN.md`** - Comprehensive test plan with all test cases and their status

For a complete overview of all implemented tests, expected test coverage, and implementation status, please refer to the [TEST_PLAN.md](./TEST_PLAN.md) file.

## Test Structure

The tests are organized into logical directories:

### `tests/config_flows/` (24 tests)
- **`test_config_flow.py`** - Main configuration flow tests (16 tests)
- **`test_reconfigure_flow.py`** - Reconfiguration flow tests (8 tests)

### `tests/cover_entities/` (100+ tests)
- **`test_integration_setup.py`** - Integration setup and loading tests
- **`test_entity_management.py`** - Platform setup and entity management tests
- **`test_entity_creation.py`** - Entity creation and initialization tests
- **`test_remapping_logic.py`** - Mathematical remapping function tests
- **`test_property_logic.py`** - Entity property behavior tests
- **`test_command_processing.py`** - Command handler tests
- **`test_convergence_logic.py`** - Position convergence tests
- **`test_service_calls.py`** - HA service call tests
- **`test_attribute_waiting.py`** - Attribute waiting and monitoring tests
- **`test_throttling_concurrency.py`** - Throttling and concurrency tests
- **`test_error_handling.py`** - Error handling and edge case tests
- **`test_state_synchronization.py`** - State sync and reporting tests
- **`test_configuration_access.py`** - Config property access tests

### `tests/` (root)
- **`helpers.py`** - Shared test utilities and constants
- **`fixtures.py`** - Shared pytest fixtures
- **`conftest.py`** - Pytest configuration and auto-fixtures

## Quick Start

### 1. Create a New Test File

```python
"""Test my new feature."""
import pytest
from homeassistant.core import HomeAssistant

# Direct imports - conftest.py handles the Python path setup
# Use the helpers and fixtures for tests
from tests.helpers import create_mock_config_entry, cleanup_platform_timers
from tests.fixtures import *  # Import all shared fixtures

@pytest.mark.asyncio
async def test_my_feature(hass: HomeAssistant, full_mock_setup, cleanup_timers):
    """Test my new feature."""
    # Your test code here
    pass
```

### 2. Available Fixtures

Import shared fixtures by adding this to your test file:

```python
# Use fixtures for new tests
from tests.fixtures import *
```

## Essential Patterns

### Basic Test Structure

```python
@pytest.mark.asyncio
async def test_something(hass: HomeAssistant, full_mock_setup, cleanup_timers):
    """Test description."""
    # full_mock_setup provides:
    # - Mock config entry
    # - Mock source cover entities
    # - Mock registries (area, device, entity)
    # - Automatic cleanup

    # cleanup_timers automatically cleans up platform timers

    # Your test logic here
    assert something_is_true
```

### Testing Config Flow

```python
from homeassistant import config_entries
from custom_components.mappedcover.const import DOMAIN

@pytest.mark.asyncio
async def test_config_flow_step(hass: HomeAssistant, mock_cover_entities):
    """Test a config flow step."""
    # Create the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Use helpers for assertions
    from tests.helpers import assert_config_flow_step
    assert_config_flow_step(result, "user", "form")

    # Submit the form
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={...}
    )
```

### Testing Entity Management

```python
@pytest.mark.asyncio
async def test_entity_behavior(hass: HomeAssistant, config_flow_entry, cleanup_timers):
    """Test entity creation and behavior."""
    # config_flow_entry provides a proper config entry created through flow

    # Setup the platform
    from tests.helpers import setup_platform_with_entities
    await setup_platform_with_entities(hass, config_flow_entry)

    # Test your entity behavior
    state = hass.states.get("cover.mapped_test_cover")
    assert state is not None
```

## Available Helpers (`tests/helpers.py`)

Below is a comprehensive reference for all helpers in `helpers.py`. Each entry includes the function/class signature, a concise description, and usage notes. You do **not** need to read the source file to use these helpers.

### Core Mocks

- **class MockThrottler**
  - `MockThrottler(*args, **kwargs)`
  - *Mock async context manager for throttling logic in tests.*
  - Usage: Patch `Throttler` in your tests to avoid real delays.

### Cleanup Utilities

- **async def cleanup_platform_timers(hass)**
  - *Cleans up lingering platform timers to prevent test warnings.*
  - Usage: Always call after tests that interact with platforms.

### Entity Setup Utilities

- **def create_mock_cover_entity(hass, entity_id, state="closed", supported_features=..., current_position=0, current_tilt_position=0, device_class="blind", attributes=None, **kwargs)**
  - *Creates a mock cover entity in the Home Assistant state machine.*
  - Usage: Use to set up a test cover entity with custom state/attributes.

- **def create_standard_mock_covers(hass)**
  - *Creates a standard set of mock cover entities for use in tests.*

### Config Entry Utilities

- **async def create_mock_config_entry(hass, entry_id=..., title=..., covers=None, **kwargs)**
  - *Creates and registers a mock config entry for mappedcover.*
  - Returns: `ConfigEntry`
  - Usage: Use for tests that require a config entry without running the full config flow.

- **async def create_config_flow_entry(hass, label="Test Mapped Cover", covers=None, **kwargs)**
  - *Creates a config entry via the normal config flow (simulates user interaction).*
  - Returns: `ConfigEntry`

### Registry Utilities

- **async def setup_mock_registries(hass, config_entry, area_name=..., device_name=..., entity_name=..., source_entity_id=...)**
  - *Sets up mock area, device, and entity registries for a test cover.*
  - Returns: `dict` with area, device, and entity registry objects and entries.

### Platform Setup Utilities

- **async def setup_platform_with_entities(hass, config_entry)**
  - *Sets up the mappedcover platform and returns the added entities.*
  - Returns: `List[MappedCover]`

### Config Flow Testing Utilities

- **async def start_config_flow(hass, context=None)**
  - *Starts a config flow and returns the initial result.*

- **async def start_reconfigure_flow(hass, config_entry)**
  - *Starts a reconfigure flow for an existing config entry.*

- **async def complete_config_flow_step(hass, flow_id, step_type="user", data=None, **kwargs)**
  - *Completes a config flow step with provided data.*

- **async def complete_user_step(hass, flow_id, label="Test Covers", covers=None)**
  - *Completes the user step of config flow.*

- **async def complete_configure_step(hass, flow_id, config_data=None, include_tilt=True)**
  - *Completes the configure step of config flow.*

- **async def complete_full_config_flow(hass, label="Test Mapped Cover", covers=None, config_data=None)**
  - *Completes a full config flow from start to finish. Returns (ConfigEntry, final flow result).*

- **async def complete_full_reconfigure_flow(hass, config_entry, label="Updated Label", covers=None, config_data=None)**
  - *Completes a full reconfigure flow from start to finish. Returns the final flow result.*

- **def assert_form_step(result, step_id, expected_fields=None)**
  - *Assert that a flow result is a form step with expected properties.*

- **def assert_create_entry(result, expected_title, expected_data=None)**
  - *Assert that a flow result creates an entry with expected properties.*

- **def assert_abort(result, expected_reason)**
  - *Assert that a flow result is an abort with expected reason.*

- **def assert_reconfigure_successful(result)**
  - *Assert that a reconfigure flow completed successfully.*

- **def assert_cleanup_successful(mapped_cover, initial_listener_count=None, initial_task_count=None)**
  - *Assert that cleanup was successful after attribute waiting.*

- **async def validate_config_flow_schema_fields(hass, step_result, expected_basic_fields, expected_tilt_fields=None, covers_with_tilt=None)**
  - *Validate that a config flow schema contains expected fields based on cover capabilities.*

### Convergence Testing Utilities

- **def create_convergence_test_setup(hass, mock_config_entry, ...)**
  - *Create a standard setup for convergence tests with a MappedCover entity.*

- **def create_convergence_state_simulator(hass, entity_id=...)**
  - *Create a state simulator that updates cover state after service calls.*

- **class ConvergenceTestContext**
  - *Context manager for convergence tests that handles common mocking patterns.*

### Assertion Helpers

- **def assert_service_called(call_tracker, service_name, **kwargs)**
  - *Assert that a service was called, optionally matching specific parameters.*
  - Usage: Use in tests to assert that a service was called, with or without specific arguments.
  - Example:
    ```python
    assert_service_called(call_tracker, "set_cover_tilt_position", tilt_position=0)
    assert_service_called(call_tracker, "set_cover_position", position=50)
    ```
  - Arguments:
    - `call_tracker`: List of (service_name, service_data) tuples (from run_unified_convergence_test)
    - `service_name`: Name of the service to check
    - `**kwargs`: Optional parameters to match in service_data

- **def assert_service_not_called(call_tracker, service_name, **kwargs)**
  - *Assert that a service was not called, optionally matching specific parameters.*
  - Usage: Use in tests to assert that a service was not called, with or without specific arguments.
  - Example:
    ```python
    assert_service_not_called(call_tracker, "set_cover_tilt_position", tilt_position=30)
    assert_service_not_called(call_tracker, "set_cover_position", position=70)
    ```
  - Arguments:
    - `call_tracker`: List of (service_name, service_data) tuples (from run_unified_convergence_test)
    - `service_name`: Name of the service to check
    - `**kwargs`: Optional parameters to match in service_data

### Attribute Waiting Testing Helpers

- **class MockedCoverManager**
  - *Manager for mapped covers created during tests with automatic cleanup.*

- **def create_test_cover_with_throttler(hass, config_entry, entity_id="cover.test_cover")**
  - *Create a MappedCover instance for testing with MockThrottler.*

- **async def wait_for_attribute_with_state_change(mapped_cover, hass, entity_id, attribute, target_value, ...)**
  - *Test waiting for attribute with optional state change during wait.*

- **async def run_attribute_waiting_test(hass, config_entry, test_scenario=..., entity_id=..., attribute=..., ...)**
  - *Run a test for attribute waiting behavior.*

- **async def test_attribute_waiting_immediate_return(hass, config_entry, **kwargs)**
  - *Test immediate return when already at target.*

- **async def test_attribute_waiting_with_timeout(hass, config_entry, **kwargs)**
  - *Test timeout behavior.*

- **async def test_attribute_waiting_with_custom_compare(hass, config_entry, compare_func, **kwargs)**
  - *Test with custom comparison function.*

- **async def test_attribute_waiting_with_unavailable_state(hass, config_entry, **kwargs)**
  - *Test with unavailable state.*

- **async def test_attribute_waiting_with_missing_attribute(hass, config_entry, **kwargs)**
  - *Test with missing attribute.*

- **async def test_early_exit_on_target_changed_event(hass, config_entry, **kwargs)**
  - *Test early exit behavior.*

- **async def test_concurrent_attribute_waits(hass, config_entry, entity_id=...)**
  - *Test multiple concurrent wait_for_attribute calls.*

- **def assert_attribute_wait_tolerance(mapped_cover, hass, entity_id, attribute, target_value, test_value, expected_result=True)**
  - *Assert that attribute waiting respects tolerance (±1 by default).*

### Command Testing Helpers

- **async def create_command_test_environment(hass, entity_id=..., current_position=..., current_tilt_position=..., supported_features=..., track_convergence=True, **kwargs)**
  - *Create a test environment optimized for command testing.*

- **async def command_with_target_validation(hass, command_func, expected_targets, should_converge=True, **env_kwargs)**
  - *Test a command and validate that it sets the expected targets.*

- **@pytest.fixture def command_funcs()**
  - *Fixture providing common command functions for testing.*

- **async def verify_command_skips_convergence(hass, command_func, condition, **env_kwargs)**
  - *Verify that a command skips convergence under specific conditions.*

- **def convert_user_to_source_position(user_pos, min_pos=10, max_pos=90)**
  - *Convert user scale position (0-100) to source scale position.*

- **def convert_user_to_source_tilt(user_tilt, min_tilt=5, max_tilt=95)**
  - *Convert user scale tilt (0-100) to source scale tilt.*

- **def assert_position_conversion(user_pos, expected_source, min_pos=10, max_pos=90)**
  - *Assert that position conversion works as expected.*

- **def assert_tilt_conversion(user_tilt, expected_source, min_tilt=5, max_tilt=95)**
  - *Assert that tilt conversion works as expected.*

- **class ServiceCallTestContext**
  - *Context manager for testing service calls with tracking and validation.*

- **def create_service_call_test_context(mapped_cover, track_calls=True, simulate_responses=False, hass=None, entity_id=...)**
  - *Create a service call test context.*

- **async def verify_timestamp_behavior(hass, command_func, should_update_timestamp=True, **env_kwargs)**
  - *Verify timestamp behavior for a command.*

### Unified Test Environment Creation

- **async def create_unified_test_environment(hass, entity_id=..., state=..., attributes=None, config_data=None, mock_registry=False, track_calls=False, mock_service_calls=False, mock_throttler=True, return_mocks=True)**
  - *Create a unified test environment combining functionality of multiple helpers.*

- **async def create_test_entity_environment(hass, **kwargs)** *(DEPRECATED)*
  - *Legacy wrapper for create_unified_test_environment.*

- **async def create_service_call_test_environment(hass, **kwargs)** *(DEPRECATED)*
  - *Legacy wrapper for create_unified_test_environment with service mocking enabled.*

### General Utilities

- **async def wait_for(condition: Callable[[], bool], timeout: float = 0.1, interval: float = 0.001) -> bool**
  - *Wait for a condition to become true, polling every interval, up to timeout seconds.*
  - Usage: Use in tests to wait for asynchronous state changes or conditions instead of fixed sleeps. Returns True if the condition became true within the timeout, False otherwise.

---

## Available Fixtures (`tests/fixtures.py`)

All fixtures are `pytest` fixtures. Use them by adding their name as a test function argument. Most are async and require `pytest.mark.asyncio`.

- **mock_config_entry** *(async, function scope)*
  - Provides: A standard mock config entry (`ConfigEntry`).

- **config_flow_entry** *(async, function scope)*
  - Provides: A config entry created through the normal config flow.
  - Requires: `mock_cover_entities` fixture.

- **mock_cover_entities** *(async, function scope)*
  - Provides: Standard mock cover entities in the Home Assistant state machine.

- **mock_area_registry** *(async, function scope)*
  - Provides: Tuple of (area_registry, area_id) for a test area.

- **mock_device_registry** *(async, function scope)*
  - Provides: Tuple of (device_registry, device_id) for a test device.
  - Requires: `mock_config_entry` fixture.

- **mock_entity_registry** *(async, function scope)*
  - Provides: Tuple of (entity_registry, entity_id) for a test entity.
  - Requires: `mock_device_registry` fixture.

- **full_mock_setup** *(async, function scope)*
  - Provides: Complete test environment with config entry, registries, and source cover state.
  - Requires: `mock_config_entry` fixture.

- **cleanup_timers** *(async, function scope, autouse)*
  - Provides: Automatic cleanup of platform timers after each test. Always included.

---

## Writing Different Types of Tests

### 1. Config Flow Tests

Test user interactions with the configuration interface:

```python
@pytest.mark.asyncio
async def test_user_step_success(hass: HomeAssistant, mock_cover_entities):
    """Test successful user step completion."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert_config_flow_step(result, "user", "form")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"covers": [TEST_COVER_ENTITY_ID]}
    )

    assert result["type"] == "create_entry"
```

### 2. Entity Management Tests

Test entity lifecycle and behavior:

```python
@pytest.mark.asyncio
async def test_entity_creation(hass: HomeAssistant, config_flow_entry, cleanup_timers):
    """Test that entities are created properly."""
    await setup_platform_with_entities(hass, config_flow_entry)

    # Check entity was created
    state = hass.states.get("cover.mapped_test_cover")
    assert state is not None
    assert state.state == "closed"
```

### 3. Integration Setup Tests

Test the overall integration setup process:

```python
@pytest.mark.asyncio
async def test_setup_success(hass: HomeAssistant, full_mock_setup, cleanup_timers):
    """Test successful integration setup."""
    # full_mock_setup handles all the mock setup

    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state == "loaded"
```

### 4. Reconfigure Flow Tests

Test configuration changes:

```python
@pytest.mark.asyncio
async def test_reconfigure_step(hass: HomeAssistant, config_flow_entry, cleanup_timers):
    """Test reconfiguration flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": config_flow_entry.entry_id},
        data=config_flow_entry.data,
    )

    assert_config_flow_step(result, "reconfigure", "form")
```

## Important Guidelines

### Always Use Timer Cleanup

**Every test should include the `cleanup_timers` fixture** to prevent lingering timer warnings:

```python
@pytest.mark.asyncio
async def test_anything(hass: HomeAssistant, cleanup_timers):
    # Your test here
```

### Use Direct Imports

Thanks to the setup in `conftest.py`, you can use direct imports without worrying about execution context:

```python
from tests.helpers import MockThrottler, cleanup_platform_timers
from tests.fixtures import full_mock_setup, cleanup_timers
```

The `conftest.py` file automatically sets up the Python path to ensure these imports work correctly whether tests are run from the project root or the tests directory.

### Mock External Dependencies

Use our standard mocks for external dependencies:

```python
# For throttling functionality
from tests.helpers import MockThrottler

# Mock the throttler in your test
with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
    # Your test code
```

### Follow Naming Conventions

- Test files: `test_*.py`
- Test functions: `test_descriptive_name`
- Fixtures: `descriptive_fixture_name`
- Mock objects: `mock_*`

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_config_flow.py

# Run with coverage
pytest tests/ --cov=custom_components.mappedcover

# Run single test
pytest tests/test_config_flow.py::test_user_step_success -v
```

## Common Patterns

### Testing Error Conditions

```python
@pytest.mark.asyncio
async def test_error_condition(hass: HomeAssistant, full_mock_setup, cleanup_timers):
    """Test that errors are handled properly."""
    with patch("some.external.call", side_effect=Exception("Test error")):
        result = await some_operation()
        assert result["type"] == "form"
        assert "errors" in result
```

### Testing State Changes

```python
@pytest.mark.asyncio
async def test_state_change(hass: HomeAssistant, config_flow_entry, cleanup_timers):
    """Test entity state changes."""
    await setup_platform_with_entities(hass, config_flow_entry)

    # Trigger state change
    hass.states.async_set("cover.test_cover", "open")
    await hass.async_block_till_done()

    # Check mapped entity state
    mapped_state = hass.states.get("cover.mapped_test_cover")
    assert mapped_state.state == "open"
```

## Maintaining Tests

When adding new features or fixing bugs:
1. Review the TEST_PLAN.md file to understand existing test coverage
2. Add new test cases to the appropriate test files
3. Update the TEST_PLAN.md file to document the new tests
4. Run the full test suite to ensure no regressions
