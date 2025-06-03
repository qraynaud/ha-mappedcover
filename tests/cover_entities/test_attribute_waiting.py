"""Test _wait_for_attribute logic for MappedCover entities."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from tests.helpers import MockThrottler
from custom_components.mappedcover.cover import MappedCover


class TestWaitForAttribute:
  """Test _wait_for_attribute method logic."""

  def setup_method(self):
    """Set up test method."""
    self.mapped_covers = []

  def teardown_method(self):
    """Clean up after test method."""
    # Clean up all mapped covers created during tests
    for mapped_cover in self.mapped_covers:
      try:
        # Cancel any running tasks
        for task in list(mapped_cover._running_tasks):
          if not task.done():
            task.cancel()
        mapped_cover._running_tasks.clear()

        # Remove any state listeners
        for remove_func in list(mapped_cover._state_listeners):
          try:
            remove_func()
          except Exception:
            pass
        mapped_cover._state_listeners.clear()
      except Exception:
        pass
    self.mapped_covers.clear()

  async def test_waits_for_attribute_to_match_target(self, hass, mock_config_entry):
    """Test that _wait_for_attribute waits for attribute to match target value."""
    # Set up initial cover state with position 30
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

      self.mapped_covers.append(mapped_cover)

    # Start waiting for position 70
    wait_task = asyncio.create_task(
      mapped_cover._wait_for_attribute("current_position", 70, timeout=5)
    )

    # Wait a bit to ensure listener is set up
    await asyncio.sleep(0.1)

    # Update state to position 50 (not target yet)
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    # Wait a bit more
    await asyncio.sleep(0.1)

    # Update state to position 70 (target reached)
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 70,
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    # Should return True when target is reached
    result = await wait_task
    assert result is True

  async def test_returns_true_immediately_if_already_at_target(self, hass, mock_config_entry):
    """Test that _wait_for_attribute returns True immediately if already at target."""
    # Set up cover state already at target position 70
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 70,
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

      self.mapped_covers.append(mapped_cover)

    # Should return True immediately
    result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=5)
    assert result is True

  async def test_timeout_behavior_returns_false(self, hass, mock_config_entry):
    """Test that _wait_for_attribute returns False on timeout."""
    # Set up cover state that won't reach target
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

      self.mapped_covers.append(mapped_cover)

    # Use very short timeout to test timeout behavior
    result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=0.1)
    assert result is False

  async def test_early_exit_when_target_changed_event_set(self, hass, mock_config_entry):
    """Test that _wait_for_attribute exits early when target_changed_event is set."""
    # Set up cover state that won't reach target
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

      self.mapped_covers.append(mapped_cover)

    # Start waiting for position 70
    wait_task = asyncio.create_task(
      mapped_cover._wait_for_attribute("current_position", 70, timeout=5)
    )

    # Wait a bit to ensure listener is set up
    await asyncio.sleep(0.1)

    # Set the target_changed_event to interrupt waiting
    mapped_cover._target_changed_event.set()

    # Should return False when interrupted
    result = await wait_task
    assert result is False

  async def test_custom_comparison_function(self, hass, mock_config_entry):
    """Test that _wait_for_attribute uses custom comparison function."""
    # Set up cover state
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

      self.mapped_covers.append(mapped_cover)

    # Custom comparison that accepts values >= target
    def custom_compare(val, target):
      return val >= target

    # Start waiting for position 65 with custom comparison
    wait_task = asyncio.create_task(
      mapped_cover._wait_for_attribute("current_position", 65, timeout=5, compare=custom_compare)
    )

    # Wait a bit to ensure listener is set up
    await asyncio.sleep(0.1)

    # Update state to position 70 (which is >= 65)
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 70,
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    # Should return True using custom comparison
    result = await wait_task
    assert result is True

  async def test_default_comparison_function_tolerance(self, hass, mock_config_entry):
    """Test that default comparison function has tolerance of ±1."""
    # Set up cover state
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

      self.mapped_covers.append(mapped_cover)

    # Start waiting for position 70
    wait_task = asyncio.create_task(
      mapped_cover._wait_for_attribute("current_position", 70, timeout=5)
    )

    # Wait a bit to ensure listener is set up
    await asyncio.sleep(0.1)

    # Update state to position 69 (within tolerance of 70)
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 69,
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    # Should return True due to tolerance
    result = await wait_task
    assert result is True

  async def test_handles_unavailable_state(self, hass, mock_config_entry):
    """Test that _wait_for_attribute handles unavailable states gracefully."""
    # Set up cover in unavailable state
    hass.states.async_set("cover.test_cover", "unavailable")

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

      self.mapped_covers.append(mapped_cover)

    # Should return False immediately for unavailable state
    result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=0.1)
    assert result is False

  async def test_handles_unknown_state(self, hass, mock_config_entry):
    """Test that _wait_for_attribute handles unknown states gracefully."""
    # Set up cover in unknown state
    hass.states.async_set("cover.test_cover", "unknown")

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

      self.mapped_covers.append(mapped_cover)

    # Should return False immediately for unknown state
    result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=0.1)
    assert result is False

  async def test_handles_missing_attribute(self, hass, mock_config_entry):
    """Test that _wait_for_attribute handles missing attribute gracefully."""
    # Set up cover state without the attribute we're looking for
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "device_class": "blind"
        # Missing current_position attribute
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

      self.mapped_covers.append(mapped_cover)

    # Should return False when attribute is missing
    result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=0.1)
    assert result is False

  async def test_handles_none_state(self, hass, mock_config_entry):
    """Test that _wait_for_attribute handles None state gracefully."""
    # Don't create any state for the cover
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.nonexistent", MockThrottler())

      self.mapped_covers.append(mapped_cover)

    # Should return False when state is None
    result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=0.1)
    assert result is False

  async def test_waits_for_tilt_attribute(self, hass, mock_config_entry):
    """Test that _wait_for_attribute works with tilt attributes."""
    # Set up cover state with tilt position 20
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 20,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

      self.mapped_covers.append(mapped_cover)

    # Start waiting for tilt position 80
    wait_task = asyncio.create_task(
      mapped_cover._wait_for_attribute("current_tilt_position", 80, timeout=5)
    )

    # Wait a bit to ensure listener is set up
    await asyncio.sleep(0.1)

    # Update state to tilt position 80
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

    # Should return True when tilt target is reached
    result = await wait_task
    assert result is True

  async def test_cleans_up_listeners_on_completion(self, hass, mock_config_entry):
    """Test that _wait_for_attribute properly cleans up listeners."""
    # Set up cover state
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

      self.mapped_covers.append(mapped_cover)

    # Verify no listeners initially
    initial_listener_count = len(mapped_cover._state_listeners)

    # Start waiting and then trigger completion
    wait_task = asyncio.create_task(
      mapped_cover._wait_for_attribute("current_position", 70, timeout=5)
    )

    # Wait a bit to ensure listener is set up
    await asyncio.sleep(0.1)

    # Verify listener was added
    assert len(mapped_cover._state_listeners) == initial_listener_count + 1

    # Update state to target to complete the wait
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 70,
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    # Wait for completion
    result = await wait_task
    assert result is True

    # Verify listener was cleaned up
    assert len(mapped_cover._state_listeners) == initial_listener_count

  async def test_cleans_up_tasks_on_completion(self, hass, mock_config_entry):
    """Test that _wait_for_attribute properly cleans up running tasks."""
    # Set up cover state
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

      self.mapped_covers.append(mapped_cover)

    # Verify no running tasks initially
    initial_task_count = len(mapped_cover._running_tasks)

    # Start waiting and then trigger completion
    wait_task = asyncio.create_task(
      mapped_cover._wait_for_attribute("current_position", 70, timeout=5)
    )

    # Wait a bit to ensure task is set up
    await asyncio.sleep(0.1)

    # Verify task was added (the event wait task)
    assert len(mapped_cover._running_tasks) >= initial_task_count

    # Update state to target to complete the wait
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 70,
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    # Wait for completion
    result = await wait_task
    assert result is True

    # Verify tasks were cleaned up
    assert len(mapped_cover._running_tasks) == initial_task_count

  async def test_cleans_up_on_timeout(self, hass, mock_config_entry):
    """Test that _wait_for_attribute properly cleans up on timeout."""
    # Set up cover state that won't reach target
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

      self.mapped_covers.append(mapped_cover)

    # Store initial counts
    initial_listener_count = len(mapped_cover._state_listeners)
    initial_task_count = len(mapped_cover._running_tasks)

    # Use very short timeout to test timeout behavior
    result = await mapped_cover._wait_for_attribute("current_position", 70, timeout=0.1)
    assert result is False

    # Verify cleanup happened
    assert len(mapped_cover._state_listeners) == initial_listener_count
    assert len(mapped_cover._running_tasks) == initial_task_count

  async def test_multiple_concurrent_waits(self, hass, mock_config_entry):
    """Test that multiple concurrent _wait_for_attribute calls work correctly."""
    # Set up cover state
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

      self.mapped_covers.append(mapped_cover)

    # Start two concurrent waits
    wait_task1 = asyncio.create_task(
      mapped_cover._wait_for_attribute("current_position", 70, timeout=5)
    )
    wait_task2 = asyncio.create_task(
      mapped_cover._wait_for_attribute("current_tilt_position", 80, timeout=5)
    )

    # Wait a bit to ensure listeners are set up
    await asyncio.sleep(0.1)

    # Update state to satisfy first wait
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 70,  # Satisfies wait_task1
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    # First wait should complete
    result1 = await wait_task1
    assert result1 is True

    # Update state to satisfy second wait
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 70,
        "current_tilt_position": 80,  # Satisfies wait_task2
        "device_class": "blind"
      }
    )

    # Second wait should complete
    result2 = await wait_task2
    assert result2 is True
