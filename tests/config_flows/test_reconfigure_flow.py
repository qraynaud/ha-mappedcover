"""Test reconfigure flow for mappedcover integration.

Tests the reconfiguration flow for existing entries including value persistence,
form rendering, and proper flow completion.
"""
import pytest
import pytest_check as check

# Import from helpers
from tests.helpers import (
    start_reconfigure_flow,
    complete_user_step,
    complete_configure_step,
    complete_full_reconfigure_flow,
    assert_form_step,
    assert_reconfigure_successful,
)

DOMAIN = "mappedcover"

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

# =============================================================================
# BASIC RECONFIGURE FLOW TESTS
# =============================================================================


async def test_reconfigure_flow_can_be_started(hass, config_flow_entry, mock_cover_entities):
    """Test that the reconfigure flow can be started for an existing mapped cover."""
    result = await start_reconfigure_flow(hass, config_flow_entry)
    assert_form_step(result, "user")


async def test_reconfigure_flow_allows_modification(hass, config_flow_entry, mock_cover_entities):
    """Test that the reconfigure flow shows existing values and allows modification."""
    result = await start_reconfigure_flow(hass, config_flow_entry)

    # Complete first step with modifications
    result2 = await complete_user_step(
        hass, result["flow_id"],
        "Updated Label",
        ["cover.real_mappedcover"]
    )

    # Complete second step with modifications
    config_data = {
        "rename_pattern": "^Cover (.*)$",
        "rename_replacement": "Window \\1",
        "min_position": 20,
        "max_position": 80,
        "min_tilt_position": 10,
        "max_tilt_position": 90,
        "close_tilt_if_down": False,
        "throttle": 200,
    }
    result3 = await complete_configure_step(hass, result2["flow_id"], config_data)

    assert_reconfigure_successful(result3)


async def test_reconfigure_flow_applies_changes(hass, config_flow_entry, mock_cover_entities):
    """Test that reconfigure flow successfully applies changes."""
    # Capture the original entry state
    original_title = config_flow_entry.title
    original_min_position = config_flow_entry.data.get("min_position", 0)

    result = await complete_full_reconfigure_flow(
        hass, config_flow_entry,
        label="Reloaded Label",
        config_data={
            "rename_pattern": "^(.*)$",
            "rename_replacement": "Mapped \\1",
            "min_position": 15,
            "max_position": 85,
            "min_tilt_position": 5,
            "max_tilt_position": 95,
            "close_tilt_if_down": True,
            "throttle": 150,
        }
    )

    # Verify the flow completed successfully
    assert_reconfigure_successful(result)

    # Verify changes were applied to the config entry
    check.equal(config_flow_entry.title, "Reloaded Label")
    check.equal(config_flow_entry.data["min_position"], 15)


async def test_reconfigure_flow_persists_changes(hass, config_flow_entry, mock_cover_entities):
    """Test that changes persist after reconfiguration."""
    original_title = config_flow_entry.title
    original_data = config_flow_entry.data.copy()

    result = await complete_full_reconfigure_flow(
        hass, config_flow_entry,
        label="Persistent Label",
        config_data={
            "rename_pattern": "^(.*)$",
            "rename_replacement": "Mapped \\1",
            "min_position": 30,
            "max_position": 70,
            "min_tilt_position": 10,
            "max_tilt_position": 90,
            "close_tilt_if_down": False,
            "throttle": 100,
        }
    )

    # Verify changes were applied (title should change to new label)
    check.equal(config_flow_entry.title, "Persistent Label")
    check.equal(config_flow_entry.data["min_position"], 30)
    check.equal(config_flow_entry.data["throttle"], 100)


async def test_reconfigure_flow_unique_id_handling(hass, config_flow_entry, mock_cover_entities):
    """Test reconfigure step with unique_id handling."""
    # Set a unique_id on the entry first
    hass.config_entries.async_update_entry(
        config_flow_entry, unique_id="test_unique_id")

    result = await start_reconfigure_flow(hass, config_flow_entry)

    # The flow should handle unique_id correctly and not abort
    assert_form_step(result, "user")


async def test_reconfigure_flow_preserves_entry_data_structure(hass, config_flow_entry, mock_cover_entities):
    """Test reconfigure preserves existing entry data structure."""
    original_entry_id = config_flow_entry.entry_id
    original_domain = config_flow_entry.domain

    result = await complete_full_reconfigure_flow(
        hass, config_flow_entry,
        label="Preserved Structure",
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

    # Entry ID and domain should remain unchanged
    check.equal(config_flow_entry.entry_id, original_entry_id)
    check.equal(config_flow_entry.domain, original_domain)


async def test_reconfigure_flow_redirects_through_user_step(hass, config_flow_entry, mock_cover_entities):
    """Test reconfigure redirects through user step correctly."""
    result = await start_reconfigure_flow(hass, config_flow_entry)

    # Should start with user step for reconfigure
    assert_form_step(result, "user")


async def test_reconfigure_vs_new_entry_code_paths(hass, config_flow_entry, mock_cover_entities):
    """Test reconfigure vs new entry code paths in async_step_configure."""
    # Test the reconfigure path
    result = await complete_full_reconfigure_flow(
        hass, config_flow_entry,
        label="Code Path Test",
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

    # Reconfigure should use abort with reconfigure_successful
    assert_reconfigure_successful(result)
