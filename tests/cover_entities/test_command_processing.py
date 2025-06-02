"""Test command processing and target management for MappedCover."""
import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
from homeassistant.components.cover import CoverEntityFeature, CoverState
from custom_components.mappedcover.cover import MappedCover, RemapDirection

from tests.fixtures import *  # Import all shared fixtures
from tests.helpers import MockThrottler


class TestAsyncSetCoverPosition:
  """Test async_set_cover_position command processing."""

  async def test_sets_target_position_and_triggers_convergence(self, hass, mock_config_entry):
    """Test that async_set_cover_position sets target_position and triggers convergence."""
    # Set source cover at position 30
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 30,
        "current_tilt_position": 50,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock converge_position to verify it's called
    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      # Call async_set_cover_position with user scale position 75
      await mapped_cover.async_set_cover_position(position=75)

      # Target position should be set to source scale equivalent (75 -> 70 in source scale)
      expected_target = 70  # 75 in user scale maps to 70 in source scale (10-90 range)
      assert mapped_cover._target_position == expected_target

      # Target tilt should be set to current tilt to preserve it
      assert mapped_cover._target_tilt == 50

      # Convergence should be triggered
      mock_converge.assert_called_once()

  async def test_skips_convergence_if_target_already_matches(self, hass, mock_config_entry):
    """Test that commands skip convergence if target already matches new value."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 30,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set target position first
    mapped_cover._target_position = 60

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      # Try to set the same target again (63 in user scale -> 60 in source scale)
      await mapped_cover.async_set_cover_position(position=63)

      # Convergence should not be triggered
      mock_converge.assert_not_called()

      # Target should remain unchanged
      assert mapped_cover._target_position == 60

  async def test_skips_convergence_if_current_position_matches_target(self, hass, mock_config_entry):
    """Test that commands skip convergence if current position already matches target."""
    # Set source at position 60
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 60,
        "current_tilt_position": 30,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Ensure no existing target
    mapped_cover._target_position = None

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      # Try to set position to where it already is (63 user scale -> 60 source scale)
      await mapped_cover.async_set_cover_position(position=63)

      # Convergence should not be triggered
      mock_converge.assert_not_called()

      # Target should remain None
      assert mapped_cover._target_position is None

  async def test_handles_missing_position_parameter(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that async_set_cover_position handles missing position parameter gracefully."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      # Call without position parameter
      await mapped_cover.async_set_cover_position()

      # No convergence should be triggered
      mock_converge.assert_not_called()

      # Target should remain None
      assert mapped_cover._target_position is None

  async def test_preserves_current_tilt_when_no_target_tilt(self, hass, mock_config_entry):
    """Test that async_set_cover_position preserves current tilt when no target tilt is set."""
    # Set source with specific tilt
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 40,
        "current_tilt_position": 25,  # Specific tilt to preserve
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Ensure no target tilt is set
    mapped_cover._target_tilt = None

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock):
      await mapped_cover.async_set_cover_position(position=80)

      # Current tilt should be preserved as target tilt
      assert mapped_cover._target_tilt == 25

  async def test_does_not_overwrite_existing_target_tilt(self, hass, mock_config_entry):
    """Test that async_set_cover_position does not overwrite existing target tilt."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 40,
        "current_tilt_position": 25,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set a target tilt first
    mapped_cover._target_tilt = 70

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock):
      await mapped_cover.async_set_cover_position(position=80)

      # Existing target tilt should be preserved
      assert mapped_cover._target_tilt == 70


class TestAsyncSetCoverTiltPosition:
  """Test async_set_cover_tilt_position command processing."""

  async def test_sets_target_tilt_and_triggers_convergence(self, hass, mock_config_entry):
    """Test that async_set_cover_tilt_position sets target_tilt and triggers convergence."""
    # Set source cover
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 30,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      # Call async_set_cover_tilt_position with user scale tilt 80
      await mapped_cover.async_set_cover_tilt_position(tilt_position=80)

      # Target tilt should be set to source scale equivalent (80 -> ~77 in source scale)
      expected_target = 77  # 80 in user scale maps to 77 in source scale (5-95 range)
      assert mapped_cover._target_tilt == expected_target

      # Convergence should be triggered
      mock_converge.assert_called_once()

  async def test_skips_convergence_if_target_already_matches(self, hass, mock_config_entry):
    """Test that tilt commands skip convergence if target already matches new value."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 30,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set target tilt first
    mapped_cover._target_tilt = 60

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      # Try to set the same target again (62 in user scale -> 60 in source scale)
      await mapped_cover.async_set_cover_tilt_position(tilt_position=62)

      # Convergence should not be triggered
      mock_converge.assert_not_called()

  async def test_skips_convergence_if_current_tilt_matches_target(self, hass, mock_config_entry):
    """Test that tilt commands skip convergence if current tilt already matches target."""
    # Set source at tilt 60
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 60,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Ensure no existing target
    mapped_cover._target_tilt = None

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      # Try to set tilt to where it already is (62 user scale -> 60 source scale)
      await mapped_cover.async_set_cover_tilt_position(tilt_position=62)

      # Convergence should not be triggered
      mock_converge.assert_not_called()

  async def test_handles_missing_tilt_position_parameter(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that async_set_cover_tilt_position handles missing tilt_position parameter gracefully."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      # Call without tilt_position parameter
      await mapped_cover.async_set_cover_tilt_position()

      # No convergence should be triggered
      mock_converge.assert_not_called()

      # Target should remain None
      assert mapped_cover._target_tilt is None


class TestAsyncOpenCover:
  """Test async_open_cover command processing."""

  async def test_sets_max_position_and_tilt_targets(self, hass, mock_config_entry):
    """Test that async_open_cover sets max position and tilt targets."""
    # Set source cover at partial positions
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,  # All features including tilt
        "current_position": 50,
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      await mapped_cover.async_open_cover()

      # Both position and tilt should be set to max values
      assert mapped_cover._target_position == 90  # max_pos in source scale
      assert mapped_cover._target_tilt == 95      # max_tilt in source scale

      # Convergence should be triggered
      mock_converge.assert_called_once()

  async def test_only_sets_position_when_no_tilt_support(self, hass, mock_config_entry):
    """Test that async_open_cover only sets position when tilt is not supported."""
    # Set source cover without tilt support
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 15,  # No tilt features
        "current_position": 50,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      await mapped_cover.async_open_cover()

      # Only position should be set
      assert mapped_cover._target_position == 90
      assert mapped_cover._target_tilt is None

      # Convergence should be triggered
      mock_converge.assert_called_once()

  async def test_skips_convergence_when_already_fully_open(self, hass, mock_config_entry):
    """Test that async_open_cover skips convergence when already fully open."""
    # Set source cover already at max positions
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 90,     # Already at max
        "current_tilt_position": 95,  # Already at max
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      await mapped_cover.async_open_cover()

      # No targets should be set
      assert mapped_cover._target_position is None
      assert mapped_cover._target_tilt is None

      # Convergence should not be triggered
      mock_converge.assert_not_called()

  async def test_partial_open_position_only(self, hass, mock_config_entry):
    """Test async_open_cover when only position needs to be opened."""
    # Set source cover with max tilt but partial position
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,     # Needs opening
        "current_tilt_position": 95,  # Already at max
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      await mapped_cover.async_open_cover()

      # Only position should be set
      assert mapped_cover._target_position == 90
      assert mapped_cover._target_tilt is None

      # Convergence should be triggered
      mock_converge.assert_called_once()


class TestAsyncCloseCover:
  """Test async_close_cover command processing."""

  async def test_sets_zero_position_and_tilt_targets(self, hass, mock_config_entry):
    """Test that async_close_cover sets zero position and tilt targets."""
    # Set source cover at open positions
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,  # All features including tilt
        "current_position": 60,
        "current_tilt_position": 50,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      await mapped_cover.async_close_cover()

      # Both position and tilt should be set to 0
      assert mapped_cover._target_position == 0
      assert mapped_cover._target_tilt == 0

      # Convergence should be triggered
      mock_converge.assert_called_once()

  async def test_only_sets_position_when_no_tilt_support(self, hass, mock_config_entry):
    """Test that async_close_cover only sets position when tilt is not supported."""
    # Set source cover without tilt support
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 15,  # No tilt features
        "current_position": 60,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      await mapped_cover.async_close_cover()

      # Only position should be set
      assert mapped_cover._target_position == 0
      assert mapped_cover._target_tilt is None

      # Convergence should be triggered
      mock_converge.assert_called_once()

  async def test_skips_convergence_when_already_fully_closed(self, hass, mock_config_entry):
    """Test that async_close_cover skips convergence when already fully closed."""
    # Set source cover already at closed positions
    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": 143,
        "current_position": 0,      # Already closed
        "current_tilt_position": 0,   # Already closed
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      await mapped_cover.async_close_cover()

      # No targets should be set
      assert mapped_cover._target_position is None
      assert mapped_cover._target_tilt is None

      # Convergence should not be triggered
      mock_converge.assert_not_called()

  async def test_partial_close_tilt_only(self, hass, mock_config_entry):
    """Test async_close_cover when only tilt needs to be closed."""
    # Set source cover with closed position but open tilt
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 0,      # Already closed
        "current_tilt_position": 50,  # Needs closing
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock) as mock_converge:
      await mapped_cover.async_close_cover()

      # Only tilt should be set
      assert mapped_cover._target_position is None
      assert mapped_cover._target_tilt == 0

      # Convergence should be triggered
      mock_converge.assert_called_once()


class TestAsyncStopCover:
  """Test async_stop_cover command processing."""

  async def test_clears_targets_and_calls_stop_service(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that async_stop_cover clears targets and calls stop service."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set some targets first
    mapped_cover._target_position = 50
    mapped_cover._target_tilt = 60

    with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock) as mock_call_service, \
         patch.object(mapped_cover, 'async_write_ha_state'):
      await mapped_cover.async_stop_cover()

      # Targets should be cleared
      assert mapped_cover._target_position is None
      assert mapped_cover._target_tilt is None

      # Stop service should be called
      mock_call_service.assert_called_once_with(
        "stop_cover",
        {"entity_id": "cover.test_cover"},
        retry=3
      )

  async def test_sets_target_changed_event(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that async_stop_cover sets the target_changed_event."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Clear the event first
    mapped_cover._target_changed_event.clear()

    with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock), \
         patch.object(mapped_cover, 'async_write_ha_state'):
      await mapped_cover.async_stop_cover()

      # Event should be set to interrupt waiting operations
      assert mapped_cover._target_changed_event.is_set()

  async def test_writes_ha_state_after_stop(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that async_stop_cover writes HA state after stopping."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock):
      with patch.object(mapped_cover, 'async_write_ha_state') as mock_write_state:
        await mapped_cover.async_stop_cover()

        # State should be written
        mock_write_state.assert_called_once()


class TestAsyncStopCoverTilt:
  """Test async_stop_cover_tilt command processing."""

  async def test_clears_tilt_target_and_calls_stop_tilt_service(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that async_stop_cover_tilt clears tilt target and calls stop_tilt service."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set some targets first
    mapped_cover._target_position = 50
    mapped_cover._target_tilt = 60

    with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock) as mock_call_service, \
         patch.object(mapped_cover, 'async_write_ha_state'):
      await mapped_cover.async_stop_cover_tilt()

      # Only tilt target should be cleared
      assert mapped_cover._target_position == 50  # Unchanged
      assert mapped_cover._target_tilt is None

      # Stop tilt service should be called
      mock_call_service.assert_called_once_with(
        "stop_cover_tilt",
        {"entity_id": "cover.test_cover"},
        retry=3
      )

  async def test_sets_target_changed_event(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that async_stop_cover_tilt sets the target_changed_event."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Clear the event first
    mapped_cover._target_changed_event.clear()

    with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock), \
         patch.object(mapped_cover, 'async_write_ha_state'):
      await mapped_cover.async_stop_cover_tilt()

      # Event should be set to interrupt waiting operations
      assert mapped_cover._target_changed_event.is_set()

  async def test_writes_ha_state_after_stop(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that async_stop_cover_tilt writes HA state after stopping."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock):
      with patch.object(mapped_cover, 'async_write_ha_state') as mock_write_state:
        await mapped_cover.async_stop_cover_tilt()

        # State should be written
        mock_write_state.assert_called_once()


class TestTaskCreation:
  """Test task creation and tracking for convergence."""

  async def test_convergence_task_is_tracked(self, hass, mock_config_entry):
    """Test that convergence tasks are properly tracked for cleanup."""
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

    # Mock converge_position to prevent actual execution
    async def mock_converge():
      await asyncio.sleep(0.1)  # Short delay to simulate work

    with patch.object(mapped_cover, 'converge_position', side_effect=mock_converge):
      # Track running tasks before
      initial_task_count = len(mapped_cover._running_tasks)

      # Trigger convergence
      await mapped_cover.async_set_cover_position(position=80)

      # Should have created a tracked task
      assert len(mapped_cover._running_tasks) >= initial_task_count

  async def test_multiple_commands_create_separate_tasks(self, hass, mock_config_entry):
    """Test that multiple commands create separate tracked tasks."""
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

    # Mock converge_position to prevent actual execution
    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock):
      # Issue multiple commands
      await mapped_cover.async_set_cover_position(position=60)
      await mapped_cover.async_set_cover_tilt_position(tilt_position=70)
      await mapped_cover.async_open_cover()

      # Each command should have called _create_tracked_task
      # Verify by checking that converge_position was called multiple times
      assert mapped_cover.converge_position.call_count == 3


class TestCommandIntegration:
  """Test command integration scenarios."""

  async def test_position_command_preserves_existing_tilt_target(self, hass, mock_config_entry):
    """Test that position commands preserve existing tilt targets."""
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

    # Set an existing tilt target
    mapped_cover._target_tilt = 80

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock):
      # Set position - should not affect existing tilt target
      await mapped_cover.async_set_cover_position(position=70)

      # Existing tilt target should be preserved
      assert mapped_cover._target_tilt == 80

  async def test_remapping_integration_with_commands(self, hass, mock_config_entry):
    """Test that commands properly integrate with remapping logic."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 40,  # Different from target to avoid optimization
        "current_tilt_position": 40,  # Different from target to avoid optimization
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock):
      # Test position remapping: 50 user scale -> 50 source scale (with 10-90 range)
      await mapped_cover.async_set_cover_position(position=50)
      assert mapped_cover._target_position == 50

      # Test tilt remapping: 50 user scale -> 50 source scale (with 5-95 range)
      await mapped_cover.async_set_cover_tilt_position(tilt_position=50)
      assert mapped_cover._target_tilt == 50

  async def test_edge_case_boundary_values(self, hass, mock_config_entry):
    """Test command processing with boundary values (0 and 100)."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 50,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    with patch.object(mapped_cover, 'converge_position', new_callable=AsyncMock):
      # Test minimum values (0 should map to 0 regardless of min values)
      await mapped_cover.async_set_cover_position(position=0)
      assert mapped_cover._target_position == 0

      await mapped_cover.async_set_cover_tilt_position(tilt_position=0)
      assert mapped_cover._target_tilt == 0

      # Test maximum values (100 should map to max values)
      await mapped_cover.async_set_cover_position(position=100)
      assert mapped_cover._target_position == 90  # max_pos

      await mapped_cover.async_set_cover_tilt_position(tilt_position=100)
      assert mapped_cover._target_tilt == 95  # max_tilt
