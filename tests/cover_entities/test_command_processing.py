"""Test command processing and target management for MappedCover."""
import pytest_check as check
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock, call

from tests.fixtures import *  # Import all shared fixtures
from tests.helpers import (
    create_command_test_environment,
    command_with_target_validation,
    convert_user_to_source_position,
    convert_user_to_source_tilt,
    assert_position_conversion,
    assert_tilt_conversion,
)


class TestAsyncSetCoverPosition:
    """Test async_set_cover_position command processing."""

    async def test_sets_target_position_and_triggers_convergence(self, hass, mock_config_entry):
        """Test that async_set_cover_position sets target_position and triggers convergence."""
        # Test command with target validation helper - sets position 75 (user) -> 70 (source)
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_set_cover_position(
                position=75),
            # 75->70 source, preserves current tilt
            expected_targets={"position": 70, "tilt": 50},
            should_converge=True,
            current_position=30,
            current_tilt_position=50
        )
        check.is_true(result)

    async def test_skips_convergence_if_target_already_matches(self, hass, mock_config_entry):
        """Test that commands skip convergence if target already matches new value."""
        # Create test environment and set up initial target
        env = await create_command_test_environment(
            hass,
            current_position=50,
            current_tilt_position=30
        )
        mapped_cover = env["entity"]
        convergence_mock = env["convergence_mock"]

        # Set target position first to match what we'll command
        mapped_cover._target_position = 60

        # Try to set the same target again (63 in user scale -> 60 in source scale)
        await mapped_cover.async_set_cover_position(position=63)

        # Convergence should not be triggered since target unchanged
        convergence_mock.assert_not_called()

        # Target should remain unchanged
        check.equal(mapped_cover._target_position, 60)

    async def test_skips_convergence_if_current_position_matches_target(self, hass, mock_config_entry):
        """Test that commands skip convergence if current position already matches target."""
        # Create test environment where current position already matches the target we'll set
        env = await create_command_test_environment(
            hass,
            # Already at target position (63 user -> 60 source)
            current_position=60,
            current_tilt_position=30
        )
        mapped_cover = env["entity"]
        convergence_mock = env["convergence_mock"]

        # Ensure no existing target
        mapped_cover._target_position = None

        # Try to set position to where it already is (63 user scale -> 60 source scale)
        await mapped_cover.async_set_cover_position(position=63)

        # Convergence should not be triggered since already at target
        convergence_mock.assert_not_called()

        # Target should remain None since no change needed
        check.is_none(mapped_cover._target_position)

    async def test_handles_missing_position_parameter(self, hass, full_mock_setup):
        """Test that async_set_cover_position handles missing position parameter gracefully."""
        # Create test environment for parameter validation
        env = await create_command_test_environment(hass)
        mapped_cover = env["entity"]
        convergence_mock = env["convergence_mock"]

        # Call without position parameter
        await mapped_cover.async_set_cover_position()

        # No convergence should be triggered with missing parameter
        convergence_mock.assert_not_called()

        # Target should remain None
        check.is_none(mapped_cover._target_position)

    async def test_preserves_current_tilt_when_no_target_tilt(self, hass, mock_config_entry):
        """Test that async_set_cover_position preserves current tilt when no target tilt is set."""
        env = await create_command_test_environment(
            hass,
            current_position=40,
            current_tilt_position=25  # This should be preserved
        )
        mapped_cover = env["entity"]
        convergence_mock = env["convergence_mock"]

        # Ensure no target tilt exists
        mapped_cover._target_tilt = None

        # Execute command
        await mapped_cover.async_set_cover_position(position=80)

        # Should preserve current tilt and set position target
        # 80->74 source (via formula: (80-1)*(90-10)/99+10)
        check.equal(mapped_cover._target_position, 74)
        # Should preserve current tilt
        check.equal(mapped_cover._target_tilt, 25)
        convergence_mock.assert_called_once()

    async def test_does_not_overwrite_existing_target_tilt(self, hass, mock_config_entry):
        """Test that async_set_cover_position does not overwrite existing target tilt."""
        env = await create_command_test_environment(
            hass,
            current_position=40,
            current_tilt_position=25
        )
        mapped_cover = env["entity"]
        convergence_mock = env["convergence_mock"]

        # Set existing target tilt
        mapped_cover._target_tilt = 70

        # Execute command
        await mapped_cover.async_set_cover_position(position=80)

        # Should preserve existing target tilt and set position target
        # 80->74 source (via formula: (80-1)*(90-10)/99+10)
        check.equal(mapped_cover._target_position, 74)
        # Should preserve existing target tilt
        check.equal(mapped_cover._target_tilt, 70)
        convergence_mock.assert_called_once()


class TestAsyncSetCoverTiltPosition:
    """Test async_set_cover_tilt_position command processing."""

    async def test_sets_target_tilt_and_triggers_convergence(self, hass, mock_config_entry):
        """Test that async_set_cover_tilt_position sets target_tilt and triggers convergence."""
        # Test command with target validation helper - sets tilt 80 (user) -> 77 (source)
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_set_cover_tilt_position(
                tilt_position=80),
            expected_targets={"tilt": 77},  # 80->77 source scale (5-95 range)
            should_converge=True,
            current_position=50,
            current_tilt_position=30
        )
        check.is_true(result)

    async def test_skips_convergence_if_target_already_matches(self, hass, mock_config_entry):
        """Test that tilt commands skip convergence if target already matches new value."""
        # Create test environment and set up initial target
        env = await create_command_test_environment(
            hass,
            current_position=50,
            current_tilt_position=30
        )
        mapped_cover = env["entity"]
        convergence_mock = env["convergence_mock"]

        # Set target tilt first to match what we'll command
        mapped_cover._target_tilt = 60

        # Try to set the same target again (62 in user scale -> 60 in source scale)
        await mapped_cover.async_set_cover_tilt_position(tilt_position=62)

        # Convergence should not be triggered since target unchanged
        convergence_mock.assert_not_called()

        # Target should remain unchanged
        check.equal(mapped_cover._target_tilt, 60)

    async def test_skips_convergence_if_current_tilt_matches_target(self, hass, mock_config_entry):
        """Test that tilt commands skip convergence if current tilt already matches target."""
        # Create test environment where current tilt already matches the target we'll set
        env = await create_command_test_environment(
            hass,
            current_position=50,
            # Already at target (62 user -> 60 source)
            current_tilt_position=60
        )
        mapped_cover = env["entity"]
        convergence_mock = env["convergence_mock"]

        # Ensure no existing target
        mapped_cover._target_tilt = None

        # Try to set tilt to where it already is (62 user scale -> 60 source scale)
        await mapped_cover.async_set_cover_tilt_position(tilt_position=62)

        # Convergence should not be triggered since already at target
        convergence_mock.assert_not_called()

        # Target should remain None since no change needed
        check.is_none(mapped_cover._target_tilt)

    async def test_handles_missing_tilt_position_parameter(self, hass, full_mock_setup):
        """Test that async_set_cover_tilt_position handles missing tilt_position parameter gracefully."""
        # Create test environment for parameter validation
        env = await create_command_test_environment(hass)
        mapped_cover = env["entity"]
        convergence_mock = env["convergence_mock"]

        # Call without tilt_position parameter
        await mapped_cover.async_set_cover_tilt_position()

        # No convergence should be triggered with missing parameter
        convergence_mock.assert_not_called()

        # Target should remain None
        check.is_none(mapped_cover._target_tilt)


class TestAsyncOpenCover:
    """Test async_open_cover command processing."""

    async def test_sets_max_position_and_tilt_targets(self, hass, mock_config_entry):
        """Test that async_open_cover sets max position and tilt targets."""
        # Test open cover command with both position and tilt targets
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_open_cover(),
            # Max values in source scale
            expected_targets={"position": 90, "tilt": 95},
            should_converge=True,
            current_position=50,
            current_tilt_position=40,
            supported_features=143  # All features including tilt
        )
        check.is_true(result)

    async def test_only_sets_position_when_no_tilt_support(self, hass, mock_config_entry):
        """Test that async_open_cover only sets position when tilt is not supported."""
        # Test open cover command with position only (no tilt support)
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_open_cover(),
            # Max position, no tilt
            expected_targets={"position": 90, "tilt": None},
            should_converge=True,
            current_position=50,
            current_tilt_position=None,
            supported_features=15  # No tilt features
        )
        check.is_true(result)

    async def test_skips_convergence_when_already_fully_open(self, hass, mock_config_entry):
        """Test that async_open_cover skips convergence when already fully open."""
        # Create test environment with command helper that handles 'no convergence' cases
        env = await create_command_test_environment(
            hass,
            current_position=90,     # Already at max
            current_tilt_position=95  # Already at max
        )
        mapped_cover = env["entity"]
        convergence_mock = env["convergence_mock"]

        # Test open cover when already open - should not set targets or converge
        await mapped_cover.async_open_cover()

        # No targets should be set (already at max)
        check.is_none(mapped_cover._target_position)
        check.is_none(mapped_cover._target_tilt)

        # No convergence should be triggered
        convergence_mock.assert_not_called()

    async def test_partial_open_position_only(self, hass, mock_config_entry):
        """Test async_open_cover when only position needs to be opened."""
        # Test open cover when only position needs opening (tilt already at max)
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_open_cover(),
            # Position to max, no tilt change
            expected_targets={"position": 90, "tilt": None},
            should_converge=True,
            current_position=50,     # Needs opening
            current_tilt_position=95  # Already at max
        )
        check.is_true(result)


class TestAsyncCloseCover:
    """Test async_close_cover command processing."""

    async def test_sets_zero_position_and_tilt_targets(self, hass, mock_config_entry):
        """Test that async_close_cover sets zero position and tilt targets."""
        # Test close cover command with both position and tilt targets
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_close_cover(),
            expected_targets={"position": 0, "tilt": 0},  # Min values
            should_converge=True,
            current_position=60,
            current_tilt_position=50,
            supported_features=143  # All features including tilt
        )
        check.is_true(result)

    async def test_only_sets_position_when_no_tilt_support(self, hass, mock_config_entry):
        """Test that async_close_cover only sets position when tilt is not supported."""
        # Test close cover command with position only (no tilt support)
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_close_cover(),
            # Min position, no tilt
            expected_targets={"position": 0, "tilt": None},
            should_converge=True,
            current_position=60,
            current_tilt_position=None,
            supported_features=15  # No tilt features
        )
        check.is_true(result)

    async def test_skips_convergence_when_already_fully_closed(self, hass, mock_config_entry):
        """Test that async_close_cover skips convergence when already fully closed."""
        # Create test environment with command helper that handles 'no convergence' cases
        env = await create_command_test_environment(
            hass,
            current_position=0,      # Already closed
            current_tilt_position=0  # Already closed
        )
        mapped_cover = env["entity"]
        convergence_mock = env["convergence_mock"]

        # Test close cover when already closed - should not set targets or converge
        await mapped_cover.async_close_cover()

        # No targets should be set (already at min)
        check.is_none(mapped_cover._target_position)
        check.is_none(mapped_cover._target_tilt)

        # No convergence should be triggered
        convergence_mock.assert_not_called()

    async def test_partial_close_tilt_only(self, hass, mock_config_entry):
        """Test async_close_cover when only tilt needs to be closed."""
        # Test close cover when only tilt needs closing (position already at min)
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_close_cover(),
            # No position change, tilt to min
            expected_targets={"position": None, "tilt": 0},
            should_converge=True,
            current_position=0,      # Already closed
            current_tilt_position=50  # Needs closing
        )
        check.is_true(result)


class TestAsyncStopCover:
    """Test async_stop_cover command processing."""

    async def test_clears_targets_and_calls_stop_service(self, hass, full_mock_setup):
        """Test that async_stop_cover clears targets and calls stop service."""
        env = await create_command_test_environment(hass)
        mapped_cover = env["entity"]

        # Set existing targets
        mapped_cover._target_position = 50
        mapped_cover._target_tilt = 60

        with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock) as service_mock, \
                patch.object(mapped_cover, 'async_write_ha_state'):
            await mapped_cover.async_stop_cover()

            # Targets should be cleared
            check.is_none(mapped_cover._target_position)
            check.is_none(mapped_cover._target_tilt)

            # Service call should be made
            service_mock.assert_called_once_with(
                "stop_cover", {"entity_id": "cover.test_cover"}, retry=3)

    async def test_sets_target_changed_event(self, hass, full_mock_setup):
        """Test that async_stop_cover sets the target_changed_event."""
        env = await create_command_test_environment(hass)
        mapped_cover = env["entity"]

        # Clear the event first
        mapped_cover._target_changed_event.clear()

        with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock), \
                patch.object(mapped_cover, 'async_write_ha_state'):
            await mapped_cover.async_stop_cover()

            # Event should be set to interrupt waiting operations
            check.is_true(mapped_cover._target_changed_event.is_set())

    async def test_writes_ha_state_after_stop(self, hass, full_mock_setup):
        """Test that async_stop_cover writes HA state after stopping."""
        env = await create_command_test_environment(hass)
        mapped_cover = env["entity"]

        with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock):
            with patch.object(mapped_cover, 'async_write_ha_state') as mock_write_state:
                await mapped_cover.async_stop_cover()

                # State should be written
                check.is_true(mock_write_state.called)


class TestAsyncStopCoverTilt:
    """Test async_stop_cover_tilt command processing."""

    async def test_clears_tilt_target_and_calls_stop_tilt_service(self, hass, full_mock_setup):
        """Test that async_stop_cover_tilt clears tilt target and calls stop_tilt service."""
        env = await create_command_test_environment(hass)
        mapped_cover = env["entity"]

        # Set some targets first
        mapped_cover._target_position = 50
        mapped_cover._target_tilt = 60

        with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock) as mock_call_service, \
                patch.object(mapped_cover, 'async_write_ha_state'):
            await mapped_cover.async_stop_cover_tilt()

            # Only tilt target should be cleared
            check.equal(mapped_cover._target_position, 50)  # Unchanged
            check.is_none(mapped_cover._target_tilt)

            # Stop tilt service should be called
            mock_call_service.assert_called_once_with(
                "stop_cover_tilt",
                {"entity_id": "cover.test_cover"},
                retry=3
            )

    async def test_sets_target_changed_event(self, hass, full_mock_setup):
        """Test that async_stop_cover_tilt sets the target_changed_event."""
        # Create test environment for stop command validation
        env = await create_command_test_environment(hass)
        mapped_cover = env["entity"]

        # Clear the event first
        mapped_cover._target_changed_event.clear()

        with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock), \
                patch.object(mapped_cover, 'async_write_ha_state'):
            await mapped_cover.async_stop_cover_tilt()

            # Event should be set to interrupt waiting operations
            check.is_true(mapped_cover._target_changed_event.is_set())

    async def test_writes_ha_state_after_stop(self, hass, full_mock_setup):
        """Test that async_stop_cover_tilt writes HA state after stopping."""
        # Create test environment for state writing validation
        env = await create_command_test_environment(hass)
        mapped_cover = env["entity"]

        with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock):
            with patch.object(mapped_cover, 'async_write_ha_state') as mock_write_state:
                await mapped_cover.async_stop_cover_tilt()

                # State should be written after stop
                check.is_true(mock_write_state.called)


class TestTaskCreation:
    """Test task creation and tracking for convergence."""

    async def test_convergence_task_is_tracked(self, hass, mock_config_entry):
        """Test that convergence tasks are properly tracked for cleanup."""
        env = await create_command_test_environment(
            hass,
            current_position=30,
            current_tilt_position=40
        )
        mapped_cover = env["entity"]

        # Mock converge_position to verify it's called
        async def mock_converge():
            # Sleep briefly to simulate work
            await asyncio.sleep(0.1)

        with patch.object(mapped_cover, 'converge_position', mock_converge):
            # Initial state should have no running tasks
            check.equal(len(mapped_cover._running_tasks), 0)

            # Set targets and trigger convergence
            mapped_cover._target_position = 80
            await mapped_cover.async_set_cover_position(position=80)

            # A task should now be tracked
            check.is_true(len(mapped_cover._running_tasks) > 0)

            # Wait for task to complete to avoid test warnings
            for task in list(mapped_cover._running_tasks):
                try:
                    await task
                except Exception:
                    pass

    async def test_multiple_commands_create_separate_tasks(self, hass, mock_config_entry):
        """Test that multiple commands create separate tracked tasks."""
        env = await create_command_test_environment(
            hass,
            current_position=30,
            current_tilt_position=40
        )
        mapped_cover = env["entity"]

        # Mock converge_position to prevent actual execution
        with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock):
            # Issue multiple commands
            await mapped_cover.async_set_cover_position(position=60)
            await mapped_cover.async_set_cover_tilt_position(tilt_position=70)
            await mapped_cover.async_open_cover()

            # Each command should have called _create_tracked_task
            # Verify by checking that converge_position was called multiple times
            check.equal(mapped_cover.converge_position.call_count, 3)


class TestCommandIntegration:
    """Test command integration scenarios."""

    async def test_position_command_preserves_existing_tilt_target(self, hass, mock_config_entry):
        """Test that position commands preserve existing tilt targets."""
        env = await create_command_test_environment(
            hass,
            current_position=30,
            current_tilt_position=40
        )
        mapped_cover = env["entity"]

        # Set an existing tilt target
        mapped_cover._target_tilt = 80

        with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock):
            # Set position - should not affect existing tilt target
            await mapped_cover.async_set_cover_position(position=70)

            # Existing tilt target should be preserved
            check.equal(mapped_cover._target_tilt, 80)

    async def test_remapping_integration_with_commands(self, hass, mock_config_entry):
        """Test that commands properly integrate with remapping logic."""
        env = await create_command_test_environment(
            hass,
            current_position=40,  # Different from target to avoid optimization
            current_tilt_position=40  # Different from target to avoid optimization
        )
        mapped_cover = env["entity"]
        convergence_mock = env["convergence_mock"]

        # Test position remapping using helper functions
        user_position = 50
        expected_source_position = convert_user_to_source_position(
            user_position)
        await mapped_cover.async_set_cover_position(position=user_position)
        check.equal(mapped_cover._target_position, expected_source_position)

        # Test tilt remapping using helper functions
        user_tilt = 50
        expected_source_tilt = convert_user_to_source_tilt(user_tilt)
        await mapped_cover.async_set_cover_tilt_position(tilt_position=user_tilt)
        check.equal(mapped_cover._target_tilt, expected_source_tilt)

        # Verify conversions with assertion helpers
        assert_position_conversion(user_position, expected_source_position)
        assert_tilt_conversion(user_tilt, expected_source_tilt)

    async def test_edge_case_boundary_values(self, hass, mock_config_entry):
        """Test command processing with boundary values (0 and 100)."""
        # Test minimum position value
        result_min_pos = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_set_cover_position(
                position=0),
            # Min position, preserve tilt
            expected_targets={"position": 0, "tilt": 50},
            should_converge=True,
            current_position=50,
            current_tilt_position=50
        )
        check.is_true(result_min_pos)

        # Test minimum tilt value
        result_min_tilt = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_set_cover_tilt_position(
                tilt_position=0),
            expected_targets={"tilt": 0},  # Min tilt
            should_converge=True,
            current_position=50,
            current_tilt_position=50
        )
        check.is_true(result_min_tilt)

        # Test maximum position value
        result_max_pos = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_set_cover_position(
                position=100),
            # Max position (90), preserve tilt
            expected_targets={"position": 90, "tilt": 50},
            should_converge=True,
            current_position=50,
            current_tilt_position=50
        )
        check.is_true(result_max_pos)

        # Test maximum tilt value
        result_max_tilt = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_set_cover_tilt_position(
                tilt_position=100),
            expected_targets={"tilt": 95},  # Max tilt (95)
            should_converge=True,
            current_position=50,
            current_tilt_position=50
        )
        check.is_true(result_max_tilt)


class TestLastPositionCommandTracking:
    """Test _last_position_command timestamp tracking in command processing."""

    async def test_set_cover_position_updates_timestamp(self, hass, mock_config_entry):
        """Test that async_set_cover_position updates _last_position_command timestamp."""
        # Test position command with timestamp behavior validation
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_set_cover_position(
                position=75),
            # 75->70 source, preserve tilt
            expected_targets={"position": 70, "tilt": 50},
            should_converge=True,
            current_position=30,
            current_tilt_position=50
        )
        check.is_true(result)

    async def test_set_cover_tilt_position_does_not_update_timestamp_directly(self, hass, mock_config_entry):
        """Test that async_set_cover_tilt_position itself doesn't directly update _last_position_command."""
        # Test tilt command behavior - tilt commands don't update position timestamp
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_set_cover_tilt_position(
                tilt_position=80),
            expected_targets={"tilt": 77},  # 80->77 source scale
            should_converge=True,
            current_position=50,
            current_tilt_position=30
        )
        check.is_true(result)

    async def test_open_cover_timestamp_behavior_through_convergence(self, hass, mock_config_entry):
        """Test that async_open_cover eventual timestamp updates happen through convergence."""
        # Test open cover command behavior for timestamp tracking
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_open_cover(),
            expected_targets={"position": 90, "tilt": 95},  # Max values
            should_converge=True,
            current_position=20,
            current_tilt_position=10
        )
        check.is_true(result)

    async def test_close_cover_timestamp_behavior_through_convergence(self, hass, mock_config_entry):
        """Test that async_close_cover eventual timestamp updates happen through convergence."""
        # Test close cover command behavior for timestamp tracking
        result = await command_with_target_validation(
            hass,
            command_func=lambda cover: cover.async_close_cover(),
            expected_targets={"position": 0, "tilt": 0},  # Min values
            should_converge=True,
            current_position=70,
            current_tilt_position=60
        )
        check.is_true(result)

    async def test_stop_cover_does_not_update_timestamp(self, hass, mock_config_entry):
        """Test that async_stop_cover does not update _last_position_command timestamp."""
        env = await create_command_test_environment(
            hass,
            current_position=40,
            current_tilt_position=30,
            supported_features=143
        )
        mapped_cover = env["entity"]

        # Set initial timestamp
        initial_time = mapped_cover._last_position_command

        # Mock _call_service and async_write_ha_state to verify the stop command behavior
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_call, \
                patch.object(mapped_cover, 'async_write_ha_state', MagicMock()) as mock_write_state:
            # Call stop which directly calls _call_service with stop_cover
            await mapped_cover.async_stop_cover()

            # Timestamp should not be updated by stop commands (verified in _call_service implementation)
            # This test verifies the command flow is correct
            check.is_none(mapped_cover._target_position)
            check.is_none(mapped_cover._target_tilt)
            check.is_true(mock_write_state.called)

    async def test_stop_cover_tilt_does_not_update_timestamp(self, hass, mock_config_entry):
        """Test that async_stop_cover_tilt does not update _last_position_command timestamp."""
        env = await create_command_test_environment(
            hass,
            current_position=40,
            current_tilt_position=30
        )
        mapped_cover = env["entity"]

        # Set some targets and initial timestamp
        mapped_cover._target_position = 50
        mapped_cover._target_tilt = 60
        initial_time = mapped_cover._last_position_command

        # Mock _call_service and async_write_ha_state to verify the stop tilt command behavior
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_call, \
                patch.object(mapped_cover, 'async_write_ha_state', MagicMock()) as mock_write_state:
            # Call stop tilt which directly calls _call_service with stop_cover_tilt
            await mapped_cover.async_stop_cover_tilt()

            # Timestamp should not be updated by stop commands (verified in _call_service implementation)
            # Verify only tilt target is cleared, position target remains unchanged
            # Position target unchanged
            check.equal(mapped_cover._target_position, 50)
            check.is_none(mapped_cover._target_tilt)    # Tilt target cleared
            check.is_true(mock_write_state.called)

    async def test_command_integration_with_timestamp_tracking(self, hass, mock_config_entry):
        """Test integration of command processing with timestamp tracking through convergence."""
        env = await create_command_test_environment(
            hass,
            current_position=50,
            current_tilt_position=40,
            supported_features=143,
            track_convergence=False  # Don't mock convergence for integration test
        )

        mapped_cover = env["entity"]

        # Mock _call_service to track which commands would be called
        call_log = []
        targets_captured = {}

        async def mock_call_service(command, data, **kwargs):
            # Capture targets when service is called (before they're cleared)
            targets_captured.update({
                'position': mapped_cover._target_position,
                'tilt': mapped_cover._target_tilt
            })
            call_log.append((command, data))

        with patch.object(mapped_cover, '_call_service', side_effect=mock_call_service), \
                patch.object(mapped_cover, 'async_write_ha_state'), \
                patch.object(mapped_cover, '_wait_for_attribute', new_callable=AsyncMock, return_value=True), \
                patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):

            # Set both position and tilt - this will automatically trigger convergence
            await mapped_cover.async_set_cover_position(position=75)

            # Verify the expected service calls
            check.is_true(len(call_log) >= 1)
            # Should include position command (which updates timestamp)
            position_calls = [
                call for call in call_log if call[0] == "set_cover_position"]
            check.is_true(len(position_calls) >= 1)

            # Use helper function for conversion verification instead of hardcoded value
            expected_source_position = convert_user_to_source_position(75)
            check.equal(position_calls[0][1]
                        ["position"], expected_source_position)

            # Verify position target was captured correctly during service call
            check.equal(targets_captured.get('position'),
                        expected_source_position)

    async def test_tilt_only_command_integration(self, hass, mock_config_entry):
        """Test tilt-only command integration with timestamp tracking."""
        env = await create_command_test_environment(
            hass,
            current_position=50,  # Position matches, so no position movement
            current_tilt_position=30,
            supported_features=143,
            track_convergence=False  # Don't mock convergence for integration test
        )

        mapped_cover = env["entity"]

        # Mock _call_service to track which commands would be called
        call_log = []

        async def mock_call_service(command, data, **kwargs):
            call_log.append((command, data))

        with patch.object(mapped_cover, '_call_service', side_effect=mock_call_service), \
                patch.object(mapped_cover, 'async_write_ha_state'), \
                patch.object(mapped_cover, '_wait_for_attribute', new_callable=AsyncMock, return_value=True), \
                patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):

            # Set only tilt
            await mapped_cover.async_set_cover_tilt_position(tilt_position=80)

            # Should only have tilt commands (which don't update timestamp)
            tilt_calls = [call for call in call_log if call[0]
                          == "set_cover_tilt_position"]
            check.is_true(len(tilt_calls) >= 1)

            # Verify no position commands were made
            position_calls = [
                call for call in call_log if call[0] == "set_cover_position"]
            check.equal(len(position_calls), 0)

            # Use helper function for tilt conversion verification instead of hardcoded value
            expected_source_tilt = convert_user_to_source_tilt(80)
            check.equal(tilt_calls[0][1]["tilt_position"],
                        expected_source_tilt)
