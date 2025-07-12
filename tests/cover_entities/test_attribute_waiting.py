"""Test _wait_for_attribute logic for MappedCover entities."""
import pytest
import asyncio

# Import from helpers
from tests.helpers import (
    create_test_cover_with_throttler,
    create_mock_cover_entity,
    wait_for_attribute_with_state_change,
)

import pytest_check as check

from tests.constants import TEST_COVER_ID, FEATURES_WITH_TILT, POSITION_MIDDLE, TILT_MIDDLE, ATTRIBUTE_WAIT_TIMEOUT, DEFAULT_DELAY


pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


class TestWaitForAttribute:
    """Test _wait_for_attribute method logic."""

    # =============================================================================
    # BASIC ATTRIBUTE WAITING TESTS
    # =============================================================================

    async def test_waits_for_attribute_to_match_target(self, hass, mock_config_entry):
        """Test that _wait_for_attribute waits for attribute to match target value."""
        # Set up initial cover state
        create_mock_cover_entity(
            hass, TEST_COVER_ID, current_position=POSITION_MIDDLE)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Test waiting with state change during wait
            result = await wait_for_attribute_with_state_change(
                mapped_cover, hass, TEST_COVER_ID, "current_position", 70, 70
            )
            check.is_true(result)
        finally:
            cover_manager.cleanup_all()

    async def test_returns_true_immediately_if_already_at_target(self, hass, mock_config_entry):
        """Test that _wait_for_attribute returns True immediately if already at target."""
        # Set up cover already at target value
        create_mock_cover_entity(hass, TEST_COVER_ID, current_position=70)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Should return True immediately
            result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=ATTRIBUTE_WAIT_TIMEOUT)
            check.is_true(result)
        finally:
            cover_manager.cleanup_all()

    async def test_timeout_behavior_returns_false(self, hass, mock_config_entry):
        """Test that _wait_for_attribute returns False on timeout."""
        # Set up cover with value different from target
        create_mock_cover_entity(
            hass, TEST_COVER_ID, current_position=POSITION_MIDDLE)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Should timeout and return False
            result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=DEFAULT_DELAY)
            check.is_false(result)
        finally:
            cover_manager.cleanup_all()

    async def test_early_exit_when_target_changed_event_set(self, hass, mock_config_entry):
        """Test that _wait_for_attribute exits early when target_changed_event is set."""
        # Set up cover with value that won't reach target
        create_mock_cover_entity(
            hass, TEST_COVER_ID, current_position=POSITION_MIDDLE)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Start waiting
            wait_task = asyncio.create_task(
                mapped_cover._wait_for_attribute(
                    "current_position", 70, timeout=ATTRIBUTE_WAIT_TIMEOUT)
            )

            # Wait briefly then set target_changed_event
            await asyncio.sleep(DEFAULT_DELAY)
            mapped_cover._target_changed_event.set()

            # Should return False when interrupted
            result = await wait_task
            check.is_false(result)
        finally:
            cover_manager.cleanup_all()

    # =============================================================================
    # COMPARISON FUNCTION TESTS
    # =============================================================================

    async def test_custom_comparison_function(self, hass, mock_config_entry):
        """Test that _wait_for_attribute uses custom comparison function."""
        # Custom comparison that accepts values >= target
        def custom_compare(val, target):
            return val >= target

        # Set up cover with initial value
        create_mock_cover_entity(
            hass, TEST_COVER_ID, current_position=POSITION_MIDDLE)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Test with custom comparison - change to 70 which should satisfy >= 65
            result = await wait_for_attribute_with_state_change(
                mapped_cover, hass, TEST_COVER_ID, "current_position", 65, 70, compare_func=custom_compare
            )
            check.is_true(result)
        finally:
            cover_manager.cleanup_all()

    async def test_default_comparison_function_tolerance(self, hass, mock_config_entry):
        """Test that _wait_for_attribute uses proper tolerance in default comparison."""
        # Set up cover with initial value
        create_mock_cover_entity(
            hass, TEST_COVER_ID, current_position=POSITION_MIDDLE)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Test that 70.4 matches target 70 (within tolerance)
            result = await wait_for_attribute_with_state_change(
                mapped_cover, hass, TEST_COVER_ID, "current_position", 70, 70.4
            )
            check.is_true(result)
        finally:
            cover_manager.cleanup_all()

    # =============================================================================
    # ERROR HANDLING & EDGE CASES
    # =============================================================================

    async def test_handles_unavailable_state(self, hass, mock_config_entry):
        """Test that _wait_for_attribute handles unavailable state."""
        # Set up cover in unavailable state
        hass.states.async_set(TEST_COVER_ID, "unavailable")

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Should return False immediately
            result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=DEFAULT_DELAY)
            check.is_false(result)
        finally:
            cover_manager.cleanup_all()

    async def test_handles_unknown_state(self, hass, mock_config_entry):
        """Test that _wait_for_attribute handles unknown state."""
        # Set up cover in unknown state
        hass.states.async_set(TEST_COVER_ID, "unknown")

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Should return False immediately
            result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=DEFAULT_DELAY)
            check.is_false(result)
        finally:
            cover_manager.cleanup_all()

    async def test_handles_missing_attribute(self, hass, mock_config_entry):
        """Test that _wait_for_attribute handles missing attribute."""
        # Set up cover without position attribute
        hass.states.async_set(
            TEST_COVER_ID,
            "open",
            {
                "supported_features": FEATURES_WITH_TILT,
                "device_class": "blind"
            }
        )

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Should return False immediately
            result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=DEFAULT_DELAY)
            check.is_false(result)
        finally:
            cover_manager.cleanup_all()

    async def test_handles_none_state(self, hass, mock_config_entry):
        """Test that _wait_for_attribute handles None state."""
        # Set up cover with None state
        hass.states.async_set(TEST_COVER_ID, None)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Should return False immediately
            result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=DEFAULT_DELAY)
            check.is_false(result)
        finally:
            cover_manager.cleanup_all()

    # =============================================================================
    # TILT ATTRIBUTES
    # =============================================================================

    async def test_waits_for_tilt_attribute(self, hass, mock_config_entry):
        """Test that _wait_for_attribute works with tilt attributes."""
        # Set up cover with initial tilt value
        create_mock_cover_entity(
            hass, TEST_COVER_ID, current_tilt_position=TILT_MIDDLE)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Test waiting for tilt position
            result = await wait_for_attribute_with_state_change(
                mapped_cover, hass, TEST_COVER_ID, "current_tilt_position", 80, 80
            )
            check.is_true(result)
        finally:
            cover_manager.cleanup_all()

    # =============================================================================
    # CLEANUP & RESOURCE MANAGEMENT
    # =============================================================================

    async def test_cleans_up_listeners_on_completion(self, hass, mock_config_entry):
        """Test that _wait_for_attribute cleans up state listeners on completion."""
        # Set up cover with initial value
        create_mock_cover_entity(
            hass, TEST_COVER_ID, current_position=POSITION_MIDDLE)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Get initial listener count
            initial_listener_count = len(mapped_cover._state_listeners)

            # Wait for attribute
            result = await wait_for_attribute_with_state_change(
                mapped_cover, hass, TEST_COVER_ID, "current_position", 70, 70
            )
            check.is_true(result)

            # Verify listener count is unchanged
            check.equal(len(mapped_cover._state_listeners),
                        initial_listener_count)
        finally:
            cover_manager.cleanup_all()

    async def test_cleans_up_tasks_on_completion(self, hass, mock_config_entry):
        """Test that _wait_for_attribute cleans up tasks on completion."""
        # Set up cover with initial value
        create_mock_cover_entity(
            hass, TEST_COVER_ID, current_position=POSITION_MIDDLE)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Get initial task count
            initial_task_count = len(mapped_cover._running_tasks)

            # Wait for attribute
            result = await wait_for_attribute_with_state_change(
                mapped_cover, hass, TEST_COVER_ID, "current_position", 70, 70
            )
            check.is_true(result)

            # Verify task count is unchanged
            check.equal(len(mapped_cover._running_tasks), initial_task_count)
        finally:
            cover_manager.cleanup_all()

    async def test_cleans_up_on_timeout(self, hass, mock_config_entry):
        """Test that _wait_for_attribute cleans up resources on timeout."""
        # Set up cover with value that won't reach target
        create_mock_cover_entity(
            hass, TEST_COVER_ID, current_position=POSITION_MIDDLE)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Get initial counts
            initial_listener_count = len(mapped_cover._state_listeners)
            initial_task_count = len(mapped_cover._running_tasks)

            # Should timeout
            result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=DEFAULT_DELAY)
            check.is_false(result)

            # Verify resources are cleaned up
            check.equal(len(mapped_cover._state_listeners),
                        initial_listener_count)
            check.equal(len(mapped_cover._running_tasks), initial_task_count)
        finally:
            cover_manager.cleanup_all()

    # =============================================================================
    # CONCURRENCY TESTS
    # =============================================================================

    async def test_multiple_concurrent_waits(self, hass, mock_config_entry):
        """Test multiple concurrent wait_for_attribute calls."""
        # Set up cover with initial values
        create_mock_cover_entity(
            hass, TEST_COVER_ID, current_position=POSITION_MIDDLE, current_tilt_position=TILT_MIDDLE)

        mapped_cover, cover_manager = create_test_cover_with_throttler(
            hass, mock_config_entry, TEST_COVER_ID)

        try:
            # Start multiple wait tasks
            wait_tasks = []
            for i in range(3):
                task = asyncio.create_task(
                    mapped_cover._wait_for_attribute(
                        "current_position", 70, timeout=ATTRIBUTE_WAIT_TIMEOUT)
                )
                wait_tasks.append(task)

            # Simulate the state change to the target value so the waits can complete
            current_state = hass.states.get(TEST_COVER_ID)
            attrs = dict(current_state.attributes)
            attrs["current_position"] = 70
            hass.states.async_set(TEST_COVER_ID, current_state.state, attrs)

            # Wait for all tasks
            results = await asyncio.gather(*wait_tasks)

            # All tasks should complete successfully
            check.is_true(all(results))
        finally:
            cover_manager.cleanup_all()
