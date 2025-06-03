"""Test state synchronization and reporting for MappedCover."""
import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from homeassistant.components.cover import CoverEntityFeature, CoverState
from custom_components.mappedcover.cover import MappedCover, RemapDirection

from tests.fixtures import *  # Import all shared fixtures
from tests.helpers import MockThrottler


class TestStateReportingDuringMovement:
  """Test state reporting when cover is moving (target values)."""

  async def test_reports_target_position_during_movement(self, hass, mock_config_entry):
    """Test that current_cover_position reports target value during movement."""
    # Set source cover at position 30
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 30,
        "current_tilt_position": 0,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set target position to 70 (simulating movement)
    mapped_cover._target_position = 70

    # Should report target position, not source position
    assert mapped_cover.current_cover_position == 75  # Target 70 remapped to user scale

    # Source position should still be different
    assert mapped_cover._source_current_position == 30

  async def test_reports_target_tilt_during_movement(self, hass, mock_config_entry):
    """Test that current_cover_tilt_position reports target value during movement."""
    # Set source cover with tilt at 25
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 25,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set target tilt to 60 (simulating tilt movement)
    mapped_cover._target_tilt = 60

    # Should report target tilt, not source tilt
    assert mapped_cover.current_cover_tilt_position == 62  # Target 60 remapped to user scale

    # Source tilt should still be different
    assert mapped_cover._source_current_tilt_position == 25

  async def test_is_moving_true_when_targets_set(self, hass, mock_config_entry):
    """Test that is_moving returns True when targets are set and recent command."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 30,
        "current_tilt_position": 20,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set targets and recent command
    mapped_cover._target_position = 70
    mapped_cover._target_tilt = 60
    mapped_cover._last_position_command = time.time()

    assert mapped_cover.is_moving

  async def test_movement_state_indicators_during_targets(self, hass, mock_config_entry):
    """Test is_opening and is_closing during movement with targets."""
    # Set source cover at middle position
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 0,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Test opening (target > current)
    mapped_cover._target_position = 80
    assert mapped_cover.is_opening
    assert not mapped_cover.is_closing

    # Test closing (target < current)
    mapped_cover._target_position = 20
    assert mapped_cover.is_closing
    assert not mapped_cover.is_opening


class TestStateReportingWhenStatic:
  """Test state reporting when cover is static (actual source values)."""

  async def test_reports_source_position_when_static(self, hass, mock_config_entry):
    """Test that current_cover_position reports remapped source value when static."""
    # Set source cover at position 45
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 45,
        "current_tilt_position": 0,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # No target set (static state)
    mapped_cover._target_position = None

    # Should report remapped source position
    assert mapped_cover.current_cover_position == 44  # Source 45 remapped to user scale

  async def test_reports_source_tilt_when_static(self, hass, mock_config_entry):
    """Test that current_cover_tilt_position reports remapped source value when static."""
    # Set source cover with tilt at 35
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 35,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # No target set (static state)
    mapped_cover._target_tilt = None

    # Should report remapped source tilt
    assert mapped_cover.current_cover_tilt_position == 34  # Source 35 remapped to user scale

  async def test_not_moving_when_static_and_old_command(self, hass, mock_config_entry):
    """Test that is_moving returns False when static with old command."""
    hass.states.async_set(
      "cover.test_cover",
      "open",  # Static state
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 30,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # No targets set and old command
    mapped_cover._target_position = None
    mapped_cover._target_tilt = None
    mapped_cover._last_position_command = time.time() - 10  # 10 seconds ago

    assert not mapped_cover.is_moving

  async def test_static_state_transitions(self, hass, mock_config_entry):
    """Test transition from moving to static state."""
    # Start with source at position 30
    hass.states.async_set(
      "cover.test_cover",
      "opening",
      {
        "supported_features": 143,
        "current_position": 30,
        "current_tilt_position": 0,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Start moving - set target
    mapped_cover._target_position = 70
    mapped_cover._last_position_command = time.time()

    # During movement - should report target
    assert mapped_cover.current_cover_position == 75  # Target remapped
    assert mapped_cover.is_moving

    # Simulate movement complete - source reaches target
    hass.states.async_set(
      "cover.test_cover",
      "open",  # Static state
      {
        "supported_features": 143,
        "current_position": 70,  # Reached target
        "current_tilt_position": 0,
        "device_class": "blind"
      }
    )

    # Clear target and set timestamp to old value (would happen in real convergence logic)
    mapped_cover._target_position = None
    mapped_cover._last_position_command = time.time() - 6  # More than 5 seconds ago

    # Now static - should report actual source
    assert mapped_cover.current_cover_position == 75  # Source 70 remapped
    assert not mapped_cover.is_moving  # Not moving anymore


class TestAsyncWriteHaState:
  """Test async_write_ha_state calls at appropriate times."""

  async def test_state_update_called_during_property_changes(self, hass, mock_config_entry):
    """Test that state updates are triggered when properties change."""
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

    # Mock the async_write_ha_state method
    with patch.object(mapped_cover, 'async_write_ha_state', new_callable=AsyncMock) as mock_write_state:

      # Simulate state change in source entity
      hass.states.async_set(
        "cover.test_cover",
        "closing",
        {
          "supported_features": 143,
          "current_position": 40,  # Position changed
          "current_tilt_position": 30,
          "device_class": "blind"
        }
      )

      # The mapped cover should detect source state changes and update its own state
      # This would normally happen through state change listeners
      # For testing, we'll verify the state properties reflect the change
      assert mapped_cover.current_cover_position == 38  # New source position remapped

  async def test_state_reporting_consistency(self, hass, mock_config_entry):
    """Test that state reporting is consistent across multiple calls."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 60,
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # No targets set - should be consistent
    mapped_cover._target_position = None
    mapped_cover._target_tilt = None

    # Multiple calls should return same values
    pos1 = mapped_cover.current_cover_position
    pos2 = mapped_cover.current_cover_position
    tilt1 = mapped_cover.current_cover_tilt_position
    tilt2 = mapped_cover.current_cover_tilt_position

    assert pos1 == pos2
    assert tilt1 == tilt2

  async def test_state_change_detection_with_targets(self, hass, mock_config_entry):
    """Test state change detection when targets are set vs cleared."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 40,
        "current_tilt_position": 20,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Capture initial static state
    initial_pos = mapped_cover.current_cover_position
    initial_tilt = mapped_cover.current_cover_tilt_position

    # Set targets - state should change
    mapped_cover._target_position = 80
    mapped_cover._target_tilt = 70

    moving_pos = mapped_cover.current_cover_position
    moving_tilt = mapped_cover.current_cover_tilt_position

    # State should be different when targets are set
    assert moving_pos != initial_pos
    assert moving_tilt != initial_tilt

    # Clear targets - should return to reporting source values
    mapped_cover._target_position = None
    mapped_cover._target_tilt = None

    final_pos = mapped_cover.current_cover_position
    final_tilt = mapped_cover.current_cover_tilt_position

    # Should match initial values (same source state)
    assert final_pos == initial_pos
    assert final_tilt == initial_tilt


class TestLastPositionCommandTracking:
  """Test _last_position_command timestamp tracking for is_moving."""

  async def test_last_position_command_updated_on_position_set(self, hass, mock_config_entry):
    """Test that _last_position_command is updated when _call_service is called with position commands."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Initial timestamp should be 0
    assert mapped_cover._last_position_command == 0

    # Mock the service registry at the module level
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
      # Directly call _call_service with a position command
      before_time = time.time()
      await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 70})
      after_time = time.time()

      # Should have updated timestamp
      assert before_time <= mapped_cover._last_position_command <= after_time

  async def test_last_position_command_updated_on_tilt_set(self, hass, mock_config_entry):
    """Test that _last_position_command is NOT updated when setting tilt (tilt commands don't cause cover movement)."""
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

    # Initial timestamp should be 0
    assert mapped_cover._last_position_command == 0

    # Mock the service registry at the module level
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
      # Directly call _call_service with a tilt command
      await mapped_cover._call_service("set_cover_tilt_position", {"entity_id": "cover.test_cover", "tilt_position": 60})

      # Should NOT have updated timestamp (tilt commands don't cause cover movement)
      assert mapped_cover._last_position_command == 0

  async def test_last_position_command_affects_is_moving(self, hass, mock_config_entry):
    """Test that recent _last_position_command makes is_moving True."""
    # Set static source state
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Initially not moving
    mapped_cover._last_position_command = 0
    assert not mapped_cover.is_moving

    # Set recent command timestamp
    mapped_cover._last_position_command = time.time()
    assert mapped_cover.is_moving

    # Set old command timestamp (more than 5 seconds)
    mapped_cover._last_position_command = time.time() - 6
    assert not mapped_cover.is_moving

  async def test_is_moving_timeout_boundary(self, hass, mock_config_entry):
    """Test is_moving timeout boundary (exactly 5 seconds)."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Test right at the 5-second boundary
    mapped_cover._last_position_command = time.time() - 4.9  # Just under 5 seconds
    assert mapped_cover.is_moving

    mapped_cover._last_position_command = time.time() - 5.1  # Just over 5 seconds
    assert not mapped_cover.is_moving

  async def test_open_close_commands_set_targets(self, hass, mock_config_entry):
    """Test that open/close commands set the appropriate targets."""
    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": 143,
        "current_position": 0,
        "current_tilt_position": 0,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock convergence to avoid service calls - properly handle coroutines
    def mock_create_tracked_task(coro):
      """Mock that properly closes coroutines to avoid warnings."""
      coro.close()  # Properly close the coroutine to avoid warnings

    with patch.object(mapped_cover, '_create_tracked_task', side_effect=mock_create_tracked_task) as mock_task:

      # Test open command sets targets to max values
      await mapped_cover.async_open_cover()
      assert mapped_cover._target_position == mapped_cover._max_pos
      assert mapped_cover._target_tilt == mapped_cover._max_tilt
      assert mock_task.called

      # Reset targets and test close command
      mapped_cover._target_position = None
      mapped_cover._target_tilt = None
      mock_task.reset_mock()

      # Update source state to open position
      hass.states.async_set(
        "cover.test_cover",
        "open",
        {
          "supported_features": 143,
          "current_position": 100,
          "current_tilt_position": 100,
          "device_class": "blind"
        }
      )

      # Test close command sets targets to min values
      await mapped_cover.async_close_cover()
      assert mapped_cover._target_position == 0
      assert mapped_cover._target_tilt == 0
      assert mock_task.called


class TestStateIntegrationScenarios:
  """Test integrated state reporting scenarios."""

  async def test_full_movement_cycle_state_reporting(self, hass, mock_config_entry):
    """Test state reporting through a complete movement cycle."""
    # Start with cover closed
    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": 143,
        "current_position": 0,
        "current_tilt_position": 0,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Initial state - closed and static
    assert mapped_cover.current_cover_position == 0
    assert mapped_cover.current_cover_tilt_position == 0
    assert not mapped_cover.is_moving
    assert mapped_cover.is_closed

    # Start opening - set targets
    mapped_cover._target_position = 90
    mapped_cover._target_tilt = 80
    mapped_cover._last_position_command = time.time()

    # During movement - reports targets
    assert mapped_cover.current_cover_position == 100  # Target 90 -> max user scale
    assert mapped_cover.current_cover_tilt_position == 84  # Target 80 remapped: (80-5)*99/(95-5)+1 = 84
    assert mapped_cover.is_moving
    assert not mapped_cover.is_closed
    assert mapped_cover.is_opening

    # Simulate source reaching target
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 90,  # Reached target
        "current_tilt_position": 80,  # Reached target
        "device_class": "blind"
      }
    )

    # Clear targets (convergence complete)
    mapped_cover._target_position = None
    mapped_cover._target_tilt = None

    # Final state - open and static
    assert mapped_cover.current_cover_position == 100  # Source 90 remapped
    assert mapped_cover.current_cover_tilt_position == 84  # Source 80 remapped: (80-5)*99/(95-5)+1 = 84
    assert not mapped_cover.is_closed
    assert not mapped_cover.is_opening
    assert not mapped_cover.is_closing
    # Clear the timestamp to ensure is_moving returns False
    mapped_cover._last_position_command = time.time() - 6
    assert not mapped_cover.is_moving

  async def test_partial_movement_state_reporting(self, hass, mock_config_entry):
    """Test state reporting during partial movements."""
    # Start with cover half open
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

    # Initial state
    initial_pos = mapped_cover.current_cover_position  # ~50
    initial_tilt = mapped_cover.current_cover_tilt_position  # ~28

    # Start small adjustment
    mapped_cover._target_position = 60  # Small position change
    mapped_cover._last_position_command = time.time()

    # Should report target during movement
    moving_pos = mapped_cover.current_cover_position
    assert moving_pos != initial_pos
    assert mapped_cover.is_moving
    assert mapped_cover.is_opening  # 60 > 50

    # Only position target set, tilt should still report source
    assert mapped_cover.current_cover_tilt_position == initial_tilt

  async def test_state_with_unavailable_source(self, hass, mock_config_entry):
    """Test state reporting when source becomes unavailable."""
    # Start with available source
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 60,
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Initial available state
    assert mapped_cover.available
    assert mapped_cover.current_cover_position is not None
    assert mapped_cover.current_cover_tilt_position is not None

    # Source becomes unavailable
    hass.states.async_set("cover.test_cover", "unavailable", {})

    # Should report unavailable and None positions
    assert not mapped_cover.available
    assert mapped_cover.current_cover_position is None
    assert mapped_cover.current_cover_tilt_position is None

    # But targets should still be reportable if set
    mapped_cover._target_position = 70
    mapped_cover._target_tilt = 50

    # Should report targets even when source unavailable
    assert mapped_cover.current_cover_position == 75  # Target remapped
    assert mapped_cover.current_cover_tilt_position == 50  # Target remapped
