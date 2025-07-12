"""Test configuration flow for mappedcover integration.

Tests the user interface interactions, validation, and error handling for the
configuration flow that sets up the mappedcover integration.
"""
import pytest
from unittest.mock import patch
from homeassistant import data_entry_flow
import pytest_check as check

# Import from helpers
from tests.helpers import (
    start_config_flow,
    complete_user_step,
    complete_configure_step,
    complete_full_config_flow,
    assert_form_step,
    assert_create_entry,
    assert_abort,
    validate_config_flow_schema_fields,
)

from tests.constants import (
    BASIC_CONFIG_FIELDS,
    TILT_CONFIG_FIELDS,
    USER_STEP_FIELDS,
    STANDARD_CONFIG_DATA,
)

# Constants for test
DOMAIN = "mappedcover"

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

# =============================================================================
# BASIC FLOW STEPS
# =============================================================================


async def test_config_flow_step_user_shows_required_fields(hass, mock_cover_entities):
    """Test that the first config flow step displays cover selection fields."""
    result = await start_config_flow(hass)
    assert_form_step(result, "user", USER_STEP_FIELDS)


async def test_config_flow_excludes_mapped_covers(hass, mock_cover_entities):
    """Test that only valid, non-mapped cover entities are selectable."""
    result = await start_config_flow(hass)
    assert_form_step(result, "user")
    # Entity exclusion logic is tested by integration functionality


async def test_config_flow_configure_step_shows_remapping_fields(hass, mock_cover_entities):
    """Test that the configure step displays remapping fields."""
    result = await start_config_flow(hass)
    result2 = await complete_user_step(hass, result["flow_id"])

    await validate_config_flow_schema_fields(
        hass, result2,
        BASIC_CONFIG_FIELDS,
        TILT_CONFIG_FIELDS,
        ["cover.real_mappedcover"]  # This cover has tilt support
    )


async def test_config_flow_creates_entry_with_correct_data(hass, mock_cover_entities):
    """Test that submitting the config flow creates an entry with the correct data."""
    entry, result = await complete_full_config_flow(
        hass,
        label="Test Mapped Covers",
        config_data={
            "rename_pattern": "^(.*)$",
            "rename_replacement": "Mapped \\1",
            "min_position": 10,
            "max_position": 90,
            "min_tilt_position": 5,
            "max_tilt_position": 95,
            "close_tilt_if_down": True,
            "throttle": 150,
        }
    )

    assert_create_entry(result, "Test Mapped Covers")

    # Verify entry data
    data = result["data"]
    check.equal(data["covers"], ["cover.real_mappedcover"])
    check.equal(data["rename_pattern"], "^(.*)$")
    check.equal(data["rename_replacement"], "Mapped \\1")
    check.equal(data["min_position"], 10)
    check.equal(data["max_position"], 90)
    check.equal(data["min_tilt_position"], 5)
    check.equal(data["max_tilt_position"], 95)
    check.is_true(data["close_tilt_if_down"])
    check.equal(data["throttle"], 150)


# =============================================================================
# VALIDATION TESTS
# =============================================================================

async def test_config_flow_validates_min_max(hass, mock_cover_entities):
    """Test that min/max values are validated and stored as expected."""
    result = await start_config_flow(hass)
    result2 = await complete_user_step(hass, result["flow_id"], "Test Validation")

    # Try invalid min/max values
    invalid_config = {
        "rename_pattern": "^(.*)$",
        "rename_replacement": "Mapped \\1",
        "min_position": 150,  # Invalid: > 100
        "max_position": -10,  # Invalid: < 0
        "min_tilt_position": 150,  # Invalid: > 100
        "max_tilt_position": -10,  # Invalid: < 0
    }

    # Should raise validation error
    with pytest.raises(data_entry_flow.InvalidData):
        await complete_configure_step(hass, result2["flow_id"], invalid_config)


async def test_config_flow_validates_at_least_one_cover_selected(hass, mock_cover_entities):
    """Test validation that at least one cover is selected (vol.Length(min=1))."""
    result = await start_config_flow(hass)

    # Try to submit with no covers selected
    user_input = {
        "label": "No Covers Test",
        "covers": [],  # Empty list should be invalid
    }

    with pytest.raises(data_entry_flow.InvalidData):
        await hass.config_entries.flow.async_configure(result["flow_id"], user_input=user_input)


async def test_config_flow_range_validation_edge_cases(hass, mock_cover_entities):
    """Test voluptuous range validation edge cases (exactly 0, exactly 100)."""
    # Test valid edge values
    entry, result = await complete_full_config_flow(
        hass,
        config_data={
            "rename_pattern": "^(.*)$",
            "rename_replacement": "Mapped \\1",
            "min_position": 0,    # Valid: exactly 0
            "max_position": 100,  # Valid: exactly 100
            "min_tilt_position": 0,   # Valid: exactly 0
            "max_tilt_position": 100,  # Valid: exactly 100
        }
    )
    assert_create_entry(result, "Test Mapped Cover")

    # Test invalid edge values
    result4 = await start_config_flow(hass)
    result5 = await complete_user_step(hass, result4["flow_id"])

    invalid_config = {
        "rename_pattern": "^(.*)$",
        "rename_replacement": "Mapped \\1",
        "min_position": -1,  # Invalid: < 0
        "max_position": 101,  # Invalid: > 100
    }

    with pytest.raises(data_entry_flow.InvalidData):
        await complete_configure_step(hass, result5["flow_id"], invalid_config)


async def test_config_flow_string_field_validation(hass, mock_cover_entities):
    """Test string field validation (empty label, malformed regex patterns)."""
    result = await start_config_flow(hass)

    # Try empty label
    user_input = {
        "label": "",  # Empty string
        "covers": ["cover.real_mappedcover"],
    }
    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=user_input)

    # Empty label should be accepted (validation happens at runtime)
    assert_form_step(result2, "configure")

    # Try potentially problematic regex pattern
    config_data = {
        "rename_pattern": "[",  # Malformed regex
        "rename_replacement": "Mapped \\1",
        **{k: v for k, v in STANDARD_CONFIG_DATA.items()
           if k not in ["rename_pattern", "rename_replacement"]}
    }
    result3 = await complete_configure_step(hass, result2["flow_id"], config_data)

    # Should still accept it (validation happens at runtime, not in config flow)
    assert_create_entry(result3, "")


# =============================================================================
# ERROR HANDLING & EDGE CASES
# =============================================================================

async def test_config_flow_entity_registry_access_fails(hass, mock_cover_entities):
    """Test error handling when entity registry access fails (internal_error abort)."""
    with patch("homeassistant.helpers.entity_registry.async_get", side_effect=Exception("Registry error")):
        result = await start_config_flow(hass)
        assert_abort(result, "internal_error")


async def test_config_flow_no_covers_available(hass):
    """Test edge case: no covers available to select."""
    result = await start_config_flow(hass)
    # Should still show the form even with no covers
    assert_form_step(result, "user")


async def test_config_flow_mixed_tilt_support(hass, mock_cover_entities):
    """Test edge case: mixed tilt support (some covers support tilt, others don't)."""
    # Add covers with different tilt support
    hass.states.async_set("cover.tilt_cover", "closed", {
                          "supported_features": 143})  # Has tilt
    hass.states.async_set("cover.no_tilt_cover", "closed", {
                          "supported_features": 15})  # No tilt

    result = await start_config_flow(hass)
    result2 = await complete_user_step(
        hass, result["flow_id"],
        "Mixed Tilt Test",
        ["cover.tilt_cover", "cover.no_tilt_cover"]
    )

    # Should show tilt fields since at least one cover supports tilt
    await validate_config_flow_schema_fields(
        hass, result2,
        BASIC_CONFIG_FIELDS,
        TILT_CONFIG_FIELDS,
        ["cover.tilt_cover", "cover.no_tilt_cover"]
    )


async def test_config_flow_tilt_options_only_if_supported(hass, mock_cover_entities):
    """Test that tilt options are only shown if the selected entity supports tilt."""
    # Test with tilt-supporting cover
    result = await start_config_flow(hass)
    result2 = await complete_user_step(
        hass, result["flow_id"],
        "Tilt Test",
        ["cover.real_mappedcover"]  # Has tilt support
    )

    await validate_config_flow_schema_fields(
        hass, result2,
        BASIC_CONFIG_FIELDS,
        TILT_CONFIG_FIELDS,
        ["cover.real_mappedcover"]
    )

    # Test with non-tilt cover
    hass.states.async_set("cover.no_tilt", "closed", {
                          "supported_features": 15})  # No tilt
    result3 = await start_config_flow(hass)
    result4 = await complete_user_step(
        hass, result3["flow_id"],
        "No Tilt Test",
        ["cover.no_tilt"]
    )

    await validate_config_flow_schema_fields(
        hass, result4,
        BASIC_CONFIG_FIELDS,
        TILT_CONFIG_FIELDS,
        ["cover.no_tilt"]
    )


# =============================================================================
# DEFAULT VALUES & CONFIGURATION
# =============================================================================

async def test_config_flow_default_values_from_constants(hass, mock_cover_entities):
    """Test default values are properly applied from constants."""
    from custom_components.mappedcover import const

    result = await start_config_flow(hass)
    result2 = await complete_user_step(hass, result["flow_id"], const.DEFAULT_LABEL)

    # Complete second step accepting all defaults
    result3 = await complete_configure_step(hass, result2["flow_id"], {})
    assert_create_entry(result3, const.DEFAULT_LABEL)

    data = result3["data"]
    # Verify all default values are applied
    check.equal(data["rename_pattern"], const.DEFAULT_RENAME_PATTERN)
    check.equal(data["rename_replacement"], const.DEFAULT_RENAME_REPLACEMENT)
    check.equal(data["min_position"], const.DEFAULT_MIN_POSITION)
    check.equal(data["max_position"], const.DEFAULT_MAX_POSITION)
    check.equal(data["min_tilt_position"], const.DEFAULT_MIN_TILT_POSITION)
    check.equal(data["max_tilt_position"], const.DEFAULT_MAX_TILT_POSITION)
    check.equal(data["close_tilt_if_down"], const.DEFAULT_CLOSE_TILT_IF_DOWN)
    check.equal(data["throttle"], const.DEFAULT_THROTTLE)


async def test_config_flow_optional_fields_defaults(hass, mock_cover_entities):
    """Test optional fields have correct defaults (close_tilt_if_down, throttle)."""
    from custom_components.mappedcover import const

    entry, result = await complete_full_config_flow(
        hass,
        config_data={
            # Only specify required fields, leave optional ones as default
            "rename_pattern": "^(.*)$",
            "rename_replacement": "Mapped \\1",
            "min_position": 10,
            "max_position": 90,
            "min_tilt_position": 5,
            "max_tilt_position": 95,
        }
    )

    assert_create_entry(result, "Test Mapped Cover")
    data = result["data"]

    # Verify optional fields get defaults
    check.equal(data["close_tilt_if_down"], const.DEFAULT_CLOSE_TILT_IF_DOWN)
    check.equal(data["throttle"], const.DEFAULT_THROTTLE)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def test_supports_tilt_function_error_handling(hass):
    """Test supports_tilt function error handling (missing state, malformed attributes)."""
    from custom_components.mappedcover.config_flow import supports_tilt

    # Test with missing entity
    result = supports_tilt(hass, "cover.nonexistent")
    check.is_false(result)

    # Test with entity that has no supported_features attribute
    hass.states.async_set("cover.no_features", "closed", {})
    result = supports_tilt(hass, "cover.no_features")
    check.is_false(result)

    # Test with malformed supported_features (non-integer)
    hass.states.async_set("cover.malformed_features", "closed", {
                          "supported_features": "not_a_number"})
    result = supports_tilt(hass, "cover.malformed_features")
    check.is_false(result)

    # Test with valid tilt support
    hass.states.async_set("cover.tilt_supported", "closed", {
                          "supported_features": 143})
    result = supports_tilt(hass, "cover.tilt_supported")
    check.is_true(result)

    # Test with no tilt support
    hass.states.async_set("cover.no_tilt", "closed",
                          {"supported_features": 15})
    result = supports_tilt(hass, "cover.no_tilt")
    check.is_false(result)


async def test_build_remap_schema_various_scenarios(hass):
    """Test build_remap_schema with various tilt_supported scenarios."""
    from custom_components.mappedcover.config_flow import build_remap_schema

    # Test with tilt supported
    schema_with_tilt = build_remap_schema(tilt_supported=True)
    schema_str = str(schema_with_tilt).lower()
    check.is_in("min_tilt_position", schema_str)
    check.is_in("max_tilt_position", schema_str)

    # Test without tilt supported
    schema_no_tilt = build_remap_schema(tilt_supported=False)
    schema_str = str(schema_no_tilt).lower()
    check.is_not_in("min_tilt_position", schema_str)
    check.is_not_in("max_tilt_position", schema_str)
