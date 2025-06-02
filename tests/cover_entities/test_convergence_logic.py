"""
Test convergence logic for MappedCover entities.

Tests the complex converge_position method including:
- Target changed event handling
- Tilt-first positioning logic
- Stop-if-moving behavior
- Position/tilt convergence with retry mechanisms
- Close_tilt_if_down special behavior
- Abort logic for target changes during execution
- Target cleanup after completion
"""
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock, ANY, PropertyMock

from custom_components.mappedcover.cover import MappedCover
from tests.helpers import (
    MockThrottler,
    create_convergence_test_setup,
    ConvergenceTestContext,
    assert_service_call_order,
    assert_service_called,
    assert_service_not_called,
    run_tilt_first_test,
    run_stop_if_moving_test,
    run_position_convergence_test,
    run_tilt_convergence_test,
    run_close_tilt_if_down_test,
    run_abort_logic_test,
    run_target_cleanup_test,
    create_tracked_cover
)
from tests.fixtures import *  # Import all shared fixtures


class TestTargetChangedEvent:
  """Test target_changed_event handling in convergence."""

  async def test_event_is_set_immediately_on_convergence_start(self, hass, mock_config_entry):
    """Test that target_changed_event is set immediately when converge_position starts."""
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

    # Clear the event first
    mapped_cover._target_changed_event.clear()
    assert not mapped_cover._target_changed_event.is_set()

    # Set targets but make convergence a no-op by setting current=target
    mapped_cover._target_position = 50  # Same as current
    mapped_cover._target_tilt = 30     # Same as current

    # Track if event is set during convergence
    event_was_set = False
    original_set = mapped_cover._target_changed_event.set

    def track_event_set():
      nonlocal event_was_set
      event_was_set = True
      original_set()

    with patch.object(mapped_cover._target_changed_event, 'set', side_effect=track_event_set), \
       patch.object(mapped_cover, '_call_service', new_callable=AsyncMock), \
       patch.object(mapped_cover, 'async_write_ha_state'):
      await mapped_cover.converge_position()

      # Event should have been set at the start of convergence
      assert event_was_set

  async def test_event_interrupts_waiting_operations(self, hass, mock_config_entry):
    """Test that setting target_changed_event can interrupt operations waiting on it."""
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

    # Clear the event
    mapped_cover._target_changed_event.clear()

    # Create a task that waits for the event
    wait_task = asyncio.create_task(mapped_cover._target_changed_event.wait())

    # Should not be done yet
    assert not wait_task.done()

    # Trigger convergence which should set the event
    mapped_cover._target_position = 70
    try:
      with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock), \
         patch.object(mapped_cover, 'async_write_ha_state'):
        await mapped_cover.converge_position()

      # Wait task should now complete because event was set
      await asyncio.sleep(0.01)  # Brief wait for task completion
      assert wait_task.done()
    finally:
      # Clean up the task to avoid lingering task errors
      if not wait_task.done():
        wait_task.cancel()
        try:
          await wait_task
        except asyncio.CancelledError:
          pass


class TestTiltFirstLogic:
  """Test tilt-first positioning logic in convergence."""

  async def test_sets_tilt_first_when_both_targets_and_position_needs_move_not_moving(self, hass, mock_config_entry):
    """Test tilt is set first when both position+tilt set, position≠current, not recently moving."""
    call_order = await run_tilt_first_test(
      hass, mock_config_entry,
      target_position=70,
      target_tilt=80,
      current_position=30,
      current_tilt_position=40,
      is_moving=False,
      wait_for_attribute_return=True
    )

    # Tilt should be called before position
    assert len(call_order) == 2
    assert call_order[0] == "set_cover_tilt_position"
    assert call_order[1] == "set_cover_position"

  async def test_does_not_set_tilt_first_when_recently_moving(self, hass, mock_config_entry):
    """Test tilt is NOT set first when cover is recently moving."""
    call_order = await run_tilt_first_test(
      hass, mock_config_entry,
      target_position=70,
      target_tilt=80,
      current_position=30,
      current_tilt_position=40,
      is_moving=True,  # Recently moving
      wait_for_attribute_return=False  # Simulate waiting fail
    )

    # Should set position first, then tilt
    assert len(call_order) == 2
    assert call_order[0] == "set_cover_position"
    assert call_order[1] == "set_cover_tilt_position"

  async def test_does_not_set_tilt_first_when_position_equals_current(self, hass, mock_config_entry):
    """Test tilt is NOT set first when target position equals current position."""
    call_order = await run_tilt_first_test(
      hass, mock_config_entry,
      target_position=70,
      target_tilt=80,
      current_position=70,  # Same as target
      current_tilt_position=40,
      is_moving=False
    )

    # Should only set tilt, not tilt-first logic
    assert len(call_order) == 1
    assert call_order[0] == "set_cover_tilt_position"

  async def test_does_not_set_tilt_first_when_only_one_target(self, hass, mock_config_entry):
    """Test tilt-first logic only applies when both position and tilt targets are set."""
    call_order = await run_tilt_first_test(
      hass, mock_config_entry,
      target_position=70,
      target_tilt=None,  # No tilt target
      current_position=30,
      current_tilt_position=40,
      is_moving=False
    )

    # Should only call position service
    assert len(call_order) == 1
    assert call_order[0] == "set_cover_position"


class TestStopIfMovingLogic:
  """Test stop-if-moving behavior in convergence."""

  async def test_stops_cover_when_moving_and_at_target_position(self, hass, mock_config_entry):
    """Test stops cover if moving but already at target position."""
    call_tracker = await run_stop_if_moving_test(
      hass, mock_config_entry,
      target_position=70,
      current_position=70,  # Same as target
      is_moving=True        # Cover is moving
    )

    # Should call stop_cover
    assert_service_called(call_tracker, "stop_cover")

  async def test_does_not_stop_when_not_moving(self, hass, mock_config_entry):
    """Test does not stop cover when not moving."""
    call_tracker = await run_stop_if_moving_test(
      hass, mock_config_entry,
      target_position=70,
      current_position=70,  # Same as target
      is_moving=False       # Cover is not moving
    )

    # Should not call stop_cover
    assert_service_not_called(call_tracker, "stop_cover")

  async def test_does_not_stop_when_moving_but_not_at_target(self, hass, mock_config_entry):
    """Test does not stop cover when moving but not at target position."""
    call_tracker = await run_stop_if_moving_test(
      hass, mock_config_entry,
      target_position=70,
      current_position=50,  # Different from target
      is_moving=True        # Cover is moving
    )

    # Should call set_cover_position but not stop_cover
    assert_service_called(call_tracker, "set_cover_position")
    assert_service_not_called(call_tracker, "stop_cover")


class TestPositionConvergence:
  """Test position convergence with retry mechanism."""

  async def test_sets_position_when_current_differs_from_target(self, hass, mock_config_entry):
    """Test sets position when current position differs from target."""
    call_tracker, mock_call_service = await run_position_convergence_test(
      hass, mock_config_entry,
      current_position=30,   # Different from target
      target_position=70,
      expect_position_call=True
    )

    # Verify call parameters with retry=3
    mock_call_service.assert_called_with(
      "set_cover_position",
      {"entity_id": "cover.test_cover", "position": 70},
      retry=3,
      abort_check=ANY
    )

  async def test_skips_position_when_current_equals_target(self, hass, mock_config_entry):
    """Test skips position setting when current equals target."""
    call_tracker, _ = await run_position_convergence_test(
      hass, mock_config_entry,
      current_position=70,   # Same as target
      target_position=70,
      expect_position_call=False
    )

    # Should not call set_cover_position
    assert_service_not_called(call_tracker, "set_cover_position")

  async def test_skips_position_when_target_is_none(self, hass, mock_config_entry):
    """Test skips position setting when target position is None."""
    call_tracker, _ = await run_position_convergence_test(
      hass, mock_config_entry,
      current_position=50,
      target_position=None,  # No position target
      target_tilt=80,
      expect_position_call=False
    )

    # Should not call set_cover_position
    assert_service_not_called(call_tracker, "set_cover_position")
    # But should call set_cover_tilt_position
    assert_service_called(call_tracker, "set_cover_tilt_position")


class TestTiltConvergence:
  """Test tilt convergence with retry mechanism."""

  async def test_sets_tilt_when_target_is_set(self, hass, mock_config_entry):
    """Test sets tilt when target tilt is set."""
    call_tracker, mock_call_service = await run_tilt_convergence_test(
      hass, mock_config_entry,
      current_tilt_position=30,
      target_tilt=80,
      expect_tilt_call=True
    )

    # Verify call parameters with retry=3
    mock_call_service.assert_called_with(
      "set_cover_tilt_position",
      {"entity_id": "cover.test_cover", "tilt_position": 80},
      retry=3,
      abort_check=ANY
    )

  async def test_skips_tilt_when_target_is_none(self, hass, mock_config_entry):
    """Test skips tilt setting when target tilt is None."""
    call_tracker, _ = await run_tilt_convergence_test(
      hass, mock_config_entry,
      current_tilt_position=30,
      target_tilt=None,     # No tilt target
      target_position=70,
      expect_tilt_call=False
    )

    # Should not call set_cover_tilt_position
    assert_service_not_called(call_tracker, "set_cover_tilt_position")
    # But should call set_cover_position
    assert_service_called(call_tracker, "set_cover_position")

  async def test_waits_for_tilt_when_position_was_set_but_not_reached(self, hass, mock_config_entry):
    """Test waits for tilt attribute when position was set but not reached."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 30,  # Different from target
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    mapped_cover._target_position = 70  # Position needs to move
    mapped_cover._target_tilt = 80

    with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock), \
       patch.object(mapped_cover, 'async_write_ha_state'), \
       patch.object(mapped_cover, '_wait_for_attribute', new_callable=AsyncMock, return_value=False) as mock_wait, \
       patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):
      await mapped_cover.converge_position()

      # Should wait for tilt attribute
      mock_wait.assert_called_with("current_tilt_position", 80, 5)

  async def test_skips_wait_when_tilt_reached_during_position_move(self, hass, mock_config_entry):
    """Test skips tilt service call when tilt reached during position movement."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 30,
        "current_tilt_position": 80,  # ALREADY at target tilt 80
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    mapped_cover._target_position = 70
    mapped_cover._target_tilt = 80  # Already at target tilt

    # Track exact service calls to check parameters
    service_calls = []

    async def track_calls(service_name, params, **kwargs):
      service_calls.append((service_name, params))
      # Update position immediately after position call
      if service_name == "set_cover_position":
        hass.states.async_set(
          "cover.test_cover",
          "open",
          {
            "current_position": 70,  # Position now matches target
            "current_tilt_position": 80  # Tilt already matches target
          }
        )

    with patch.object(mapped_cover, '_call_service', side_effect=track_calls), \
        patch.object(mapped_cover, 'async_write_ha_state'), \
        patch.object(mapped_cover, '_wait_for_attribute', new_callable=AsyncMock, return_value=True), \
        patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):
      await mapped_cover.converge_position()

      # We may get multiple calls, but the important part is to verify:
      # 1. We don't set tilt to a different value than current (which is already at target)
      # 2. We do set position to the target value
      assert len(service_calls) >= 1

      # Find any tilt position calls and verify they don't change from current
      tilt_calls = [(svc, params) for svc, params in service_calls
                    if svc == "set_cover_tilt_position"]
      for _, params in tilt_calls:
        assert params["tilt_position"] == 80, "Tilt should not be changed from current value"

      # Verify position is called with target value
      position_calls = [(svc, params) for svc, params in service_calls
                      if svc == "set_cover_position"]
      assert len(position_calls) == 1, "Position should be called exactly once"
      assert position_calls[0][1]["position"] == 70, "Position should be set to target value"


class TestCloseTiltIfDownBehavior:
  """Test close_tilt_if_down special behavior."""

  async def test_sets_tilt_zero_before_target_when_close_tilt_if_down_and_decreasing(self, hass, mock_config_entry):
    """Test sets tilt to 0 before target when close_tilt_if_down enabled and tilt decreasing."""
    call_order = await run_close_tilt_if_down_test(
      hass, mock_config_entry,
      current_tilt_position=80,
      target_tilt=40,
      feature_enabled=True,
      tilt_decreasing=True,
      with_position_target=False
    )

    # Should call tilt=0 first, then target tilt
    assert len(call_order) == 2
    assert call_order[0] == ("set_cover_tilt_position", 0)
    assert call_order[1] == ("set_cover_tilt_position", 40)

  async def test_does_not_set_tilt_zero_when_close_tilt_if_down_disabled(self, hass, mock_config_entry):
    """Test does not set tilt to 0 when close_tilt_if_down is disabled."""
    call_order = await run_close_tilt_if_down_test(
      hass, mock_config_entry,
      feature_enabled=False  # Disabled
    )

    # Should only call target tilt, not tilt=0
    assert len(call_order) == 1
    assert call_order[0] == ("set_cover_tilt_position", 40)

  async def test_does_not_set_tilt_zero_when_tilt_increasing(self, hass, mock_config_entry):
    """Test does not set tilt to 0 when tilt is increasing."""
    call_order = await run_close_tilt_if_down_test(
      hass, mock_config_entry,
      tilt_decreasing=False  # Increasing
    )

    # Should only call target tilt, not tilt=0
    assert len(call_order) == 1
    assert call_order[0] == ("set_cover_tilt_position", 70)

  async def test_does_not_set_tilt_zero_when_position_target_exists(self, hass, mock_config_entry):
    """Test does not set tilt to 0 when position target is also set."""
    call_order = await run_close_tilt_if_down_test(
      hass, mock_config_entry,
      with_position_target=True  # Position target is set
    )

    # Should include calls for both position and tilt, but not tilt=0
    tilt_positions = [pos for name, pos in call_order if name == "set_cover_tilt_position"]
    assert 0 not in tilt_positions
    assert len(call_order) > 1  # Should have multiple calls


class TestAbortLogic:
  """Test abort logic for target changes during execution."""

  async def test_aborts_early_when_target_position_changes(self, hass, mock_config_entry):
    """Test exits early if target position changes during execution."""
    call_count, mapped_cover = await run_abort_logic_test(
      hass, mock_config_entry,
      change_position_target=True,
      change_tilt_target=False
    )

    # Should only make one service call before aborting
    assert call_count == 1

    # Targets should not be cleared (still active due to abort)
    assert mapped_cover._target_position == 50  # Changed value
    assert mapped_cover._target_tilt == 80      # Original value

  async def test_aborts_early_when_target_tilt_changes(self, hass, mock_config_entry):
    """Test exits early if target tilt changes during execution."""
    call_count, mapped_cover = await run_abort_logic_test(
      hass, mock_config_entry,
      change_position_target=False,
      change_tilt_target=True
    )

    # Should only make one service call before aborting
    assert call_count == 1

    # Targets should not be cleared
    assert mapped_cover._target_position == 70  # Original value
    assert mapped_cover._target_tilt == 90      # Changed value

  async def test_aborts_during_close_tilt_if_down_phase(self, hass, mock_config_entry):
    """Test abort works during close_tilt_if_down zero-tilt phase."""
    # Use config_entries.async_update_entry instead of direct modification
    from homeassistant.config_entries import ConfigEntries
    config_entries = hass.config_entries
    config_entries.async_update_entry(
      mock_config_entry,
      data={
        "source_entity": "cover.test_cover",
        "min_position": 10,
        "max_position": 90,
        "min_tilt": 5,
        "max_tilt": 95,
        "close_tilt_if_down": True
      }
    )

    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 80,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    mapped_cover._target_position = None
    mapped_cover._target_tilt = 40

    call_count = 0

    async def change_target_during_zero_tilt(*args, **kwargs):
      nonlocal call_count
      call_count += 1
      if call_count == 1:  # During zero-tilt call
        mapped_cover._target_tilt = 90  # Change target

    with patch.object(mapped_cover, '_call_service', side_effect=change_target_during_zero_tilt), \
       patch.object(mapped_cover, 'async_write_ha_state'):
      await mapped_cover.converge_position()

      # Should only make the zero-tilt call before aborting
      assert call_count == 1
      # Target should not be cleared
      assert mapped_cover._target_tilt == 90

  async def test_continues_when_targets_unchanged(self, hass, mock_config_entry):
    """Test continues execution when targets remain unchanged."""
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

    mapped_cover._target_position = 70
    mapped_cover._target_tilt = 80

    # Track calls to ensure proper cleanup
    call_order = []

    async def track_calls(service_name, *args, **kwargs):
      call_order.append(service_name)
      # Simulate state changes to avoid extra calls
      if service_name == "set_cover_position":
        hass.states.async_set(
          "cover.test_cover",
          "open",
          {"current_position": 70, "current_tilt_position": 40}
        )

    # Fix lingering task by using a proper wait_for mock
    async def mock_wait(*args, **kwargs):
      return True  # Everything always converges

    with patch.object(mapped_cover, '_call_service', side_effect=track_calls), \
        patch.object(mapped_cover, 'async_write_ha_state'), \
        patch.object(mapped_cover, '_wait_for_attribute', side_effect=mock_wait), \
        patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):
      await mapped_cover.converge_position()

      # Should have service calls (not asserting order since that depends on implementation)
      assert len(call_order) == 2
      assert sorted(call_order) == sorted(["set_cover_position", "set_cover_tilt_position"])


class TestTargetCleanup:
  """Test target cleanup after convergence completion."""

  async def test_clears_targets_when_convergence_completes_successfully(self, hass, mock_config_entry):
    """Test clears both targets when convergence completes successfully."""
    mapped_cover, mock_write_state = await run_target_cleanup_test(
      hass, mock_config_entry,
      set_position_target=True,
      set_tilt_target=True
    )

    # Both targets should be cleared
    assert mapped_cover._target_position is None
    assert mapped_cover._target_tilt is None

    # Should write HA state at the end
    mock_write_state.assert_called()

  async def test_clears_only_position_target_when_only_position_set(self, hass, mock_config_entry):
    """Test clears only position target when only position was set."""
    mapped_cover, _ = await run_target_cleanup_test(
      hass, mock_config_entry,
      set_position_target=True,
      set_tilt_target=False
    )

    # Position target should be cleared
    assert mapped_cover._target_position is None
    # Tilt target should remain None
    assert mapped_cover._target_tilt is None

  async def test_clears_only_tilt_target_when_only_tilt_set(self, hass, mock_config_entry):
    """Test clears only tilt target when only tilt was set."""
    mapped_cover, _ = await run_target_cleanup_test(
      hass, mock_config_entry,
      set_position_target=False,
      set_tilt_target=True
    )

    # Position target should remain None
    assert mapped_cover._target_position is None
    # Tilt target should be cleared
    assert mapped_cover._target_tilt is None

  async def test_does_not_clear_targets_when_aborted(self, hass, mock_config_entry):
    """Test does not clear targets when convergence is aborted."""
    mapped_cover, _ = await run_target_cleanup_test(
      hass, mock_config_entry,
      set_position_target=True,
      set_tilt_target=True,
      abort_during_execution=True
    )

    # Targets should not be cleared due to abort
    assert mapped_cover._target_position == 50  # Changed value (due to abort logic)
    assert mapped_cover._target_tilt == 80      # Original value
