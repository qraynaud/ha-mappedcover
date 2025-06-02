# Testing Guide for MappedCover Integration

This guide helps you write tests for the MappedCover Home Assistant integration. Our test infrastructure provides shared utilities, fixtures, and patterns to make testing easier and more consistent.

## Test Structure

The tests are organized into logical directories:

### `tests/config_flows/`
- **`test_config_flow.py`** - Main configuration flow tests
- **`test_reconfigure_flow.py`** - Reconfiguration flow tests

### `tests/cover_entities/`
- **`test_integration_setup.py`** - Integration setup and loading tests
- **`test_entity_management.py`** - Platform setup and entity management tests

### `tests/` (root)
- **`helpers.py`** - Shared test utilities and constants
- **`fixtures.py`** - Shared pytest fixtures
- **`conftest.py`** - Pytest configuration and auto-fixtures
- **`README.md`** - This testing guide

## Quick Start

### 1. Create a New Test File

```python
"""Test my new feature."""
import pytest
from homeassistant.core import HomeAssistant

# Direct imports - conftest.py handles the Python path setup
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

## Available Utilities

### Core Helpers (`tests/helpers.py`)

#### Mock Creation
- `create_mock_cover_entity(entity_id, features=None)` - Creates mock cover entities
- `create_mock_config_entry(data=None)` - Creates config entries for testing
- `create_standard_mock_covers()` - Creates the standard test cover set

#### Setup Helpers
- `setup_mock_registries(hass)` - Sets up area, device, and entity registries
- `setup_platform_with_entities(hass, config_entry)` - Sets up the mappedcover platform
- `create_config_flow_entry(hass, data=None)` - Creates entries via config flow

#### Cleanup
- `cleanup_platform_timers(hass)` - Cleans up lingering platform timers (prevents warnings)

#### Assertions
- `assert_config_flow_step(result, expected_type, expected_step_id)` - Assert config flow steps
- `assert_form_schema_contains(schema, expected_keys)` - Assert form contains keys

#### Constants
```python
# Test entity IDs
TEST_COVER_ENTITY_ID = "cover.test_cover"
TEST_AREA_ID = "test_area"
TEST_DEVICE_NAME = "Test Device"

# Feature sets
FEATURES_BASIC = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
FEATURES_WITH_TILT = FEATURES_BASIC | CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT

# Standard config data
MOCK_COVERS_CONFIG = {...}  # Standard test configuration
```

### Fixtures (`tests/fixtures.py`)

#### Basic Fixtures
- `mock_config_entry` - Standard mock config entry
- `mock_source_cover_state` - Mock state for source entities
- `mock_cover_entities` - Standard mock cover entity setup

#### Registry Fixtures
- `mock_area_registry` - Area registry with test area
- `mock_device_registry` - Device registry with test device
- `mock_entity_registry` - Entity registry with source cover

#### Complete Setup
- `full_mock_setup` - Complete setup with all mocks and cleanup
- `config_flow_entry` - Config entry created through proper flow
- `cleanup_timers` - Automatic timer cleanup (use in every test!)

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

## Extending the Test Infrastructure

### Adding New Helpers

Add new helper functions to `tests/helpers.py`:

```python
def create_my_new_helper(param1, param2=None):
    """Helper for common test pattern."""
    # Implementation here
    return result
```

### Adding New Fixtures

Add new fixtures to `tests/fixtures.py`:

```python
@pytest.fixture
async def my_fixture(hass: HomeAssistant):
    """Fixture description."""
    # Setup code
    yield fixture_value
    # Cleanup code
```

### Adding New Constants

Add new test constants to `tests/helpers.py`:

```python
# At the top of helpers.py
NEW_TEST_CONSTANT = "test_value"
```

This infrastructure provides a solid foundation for comprehensive testing while maintaining consistency and reducing code duplication.
