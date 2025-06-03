"""Test service call logic for MappedCover._call_service method."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
import logging
import time

from homeassistant.components.cover import CoverEntityFeature, CoverState
from custom_components.mappedcover.cover import MappedCover

from tests.fixtures import *  # Import all shared fixtures
from tests.helpers import MockThrottler


class TestCallServiceThrottling:
  """Test that _call_service uses the throttler correctly."""

  async def test_throttler_is_used(self, hass, mock_config_entry):
    """Test that _call_service uses the throttler to limit call frequency."""
    # Set up test cover
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

    # Create a mock throttler to track its usage
    mock_throttler = MagicMock()
    mock_throttler.__aenter__ = AsyncMock()
    mock_throttler.__aexit__ = AsyncMock()

    # Create the cover entity with our mock throttler
    with patch("custom_components.mappedcover.cover.Throttler", return_value=mock_throttler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", mock_throttler)

    # Mock the service call method at module level
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_async_call:
      await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70}
      )

      # Assert that the throttler was used
      mock_throttler.__aenter__.assert_called_once()
      mock_throttler.__aexit__.assert_called_once()

      # Assert that the service was called with correct parameters
      mock_async_call.assert_called_once_with(
        "cover", "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70},
        blocking=True
      )


class TestAllowedCommands:
  """Test that _call_service validates the allowed commands."""

  async def test_valid_commands_are_accepted(self, hass, mock_config_entry):
    """Test that valid commands are accepted."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    allowed_commands = [
      "set_cover_position",
      "set_cover_tilt_position",
      "stop_cover",
      "stop_cover_tilt"
    ]

    # Mock the service call
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_async_call:
      # Test each allowed command
      for command in allowed_commands:
        result = await mapped_cover._call_service(
          command,
          {"entity_id": "cover.test_cover"}
        )
        assert result is True, f"Command {command} should be allowed"

  async def test_invalid_commands_raise_value_error(self, hass, mock_config_entry):
    """Test that invalid commands raise ValueError."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    invalid_commands = [
      "open_cover",  # Not in allowed list
      "close_cover", # Not in allowed list
      "invalid_command",
      ""
    ]

    # Test each invalid command
    for command in invalid_commands:
      with pytest.raises(ValueError, match=f"Command {command} not allowed"):
        await mapped_cover._call_service(
          command,
          {"entity_id": "cover.test_cover"}
        )

  async def test_set_cover_position_updates_timestamp(self, hass, mock_config_entry):
    """Test that set_cover_position command updates _last_position_command timestamp."""
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Store initial timestamp (should be 0)
    initial_timestamp = mapped_cover._last_position_command
    assert initial_timestamp == 0

    # Mock the service call
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_async_call:
      # Call set_cover_position
      await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70}
      )

      # Timestamp should now be updated (greater than initial)
      assert mapped_cover._last_position_command > initial_timestamp

  async def test_set_cover_tilt_position_does_not_update_timestamp(self, hass, mock_config_entry):
    """Test that set_cover_tilt_position command does NOT update _last_position_command timestamp."""
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Store initial timestamp (should be 0)
    initial_timestamp = mapped_cover._last_position_command
    assert initial_timestamp == 0

    # Mock the service call
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_async_call:
      # Call set_cover_tilt_position
      await mapped_cover._call_service(
        "set_cover_tilt_position",
        {"entity_id": "cover.test_cover", "tilt_position": 80}
      )

      # Timestamp should still be 0 (not updated for tilt commands)
      assert mapped_cover._last_position_command == initial_timestamp

  async def test_stop_commands_do_not_update_timestamp(self, hass, mock_config_entry):
    """Test that stop commands do NOT update _last_position_command timestamp."""
    hass.states.async_set(
      "cover.test_cover",
      "opening",
      {
        "supported_features": 143,
        "current_position": 50,
        "current_tilt_position": 40,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Store initial timestamp (should be 0)
    initial_timestamp = mapped_cover._last_position_command
    assert initial_timestamp == 0

    # Mock the service call
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_async_call:
      # Test stop_cover
      await mapped_cover._call_service(
        "stop_cover",
        {"entity_id": "cover.test_cover"}
      )

      # Timestamp should still be 0
      assert mapped_cover._last_position_command == initial_timestamp

      # Test stop_cover_tilt
      await mapped_cover._call_service(
        "stop_cover_tilt",
        {"entity_id": "cover.test_cover"}
      )

      # Timestamp should still be 0
      assert mapped_cover._last_position_command == initial_timestamp

  async def test_multiple_position_commands_update_timestamp(self, hass, mock_config_entry):
    """Test that multiple position commands update timestamp progressively."""
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock the service call
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_async_call:
      # First position command
      await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 30}
      )
      
      first_timestamp = mapped_cover._last_position_command
      assert first_timestamp is not None

      # Small delay to ensure different timestamps
      await asyncio.sleep(0.01)

      # Second position command
      await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 80}
      )
      
      second_timestamp = mapped_cover._last_position_command
      assert second_timestamp is not None
      assert second_timestamp > first_timestamp


class TestPositionConfirmation:
  """Test position confirmation with _wait_for_attribute when retry>0."""

  async def test_waits_for_position_confirmation_when_retry_specified(self, hass, mock_config_entry):
    """Test that _call_service waits for position confirmation when retry>0."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock _wait_for_attribute to return True (position reached)
    mock_wait_for_attribute = AsyncMock(return_value=True)

    with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
       patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):

      result = await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70},
        retry=3
      )

      # Assert _wait_for_attribute was called with correct parameters
      mock_wait_for_attribute.assert_called_once_with(
        "current_position", 70, timeout=30
      )

      # Service call should return True when position is reached
      assert result is True

  async def test_retries_on_position_confirmation_failure(self, hass, mock_config_entry):
    """Test that _call_service retries when position confirmation fails."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock _wait_for_attribute to always return False (position not reached)
    mock_wait_for_attribute = AsyncMock(return_value=False)

    with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
       patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()), \
       patch("asyncio.sleep", AsyncMock()):

      result = await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70},
        retry=2
      )

      # Should be called 1 + retry (3) times
      assert mock_wait_for_attribute.call_count == 3

      # Service call should return False after all retries fail
      assert result is False

  async def test_no_wait_for_position_when_retry_zero(self, hass, mock_config_entry):
    """Test that _call_service doesn't wait for position confirmation when retry=0."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock _wait_for_attribute to track if it's called
    mock_wait_for_attribute = AsyncMock(return_value=True)

    with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
       patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):

      result = await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70},
        retry=0  # No retries
      )

      # _wait_for_attribute should not be called
      mock_wait_for_attribute.assert_not_called()

      # Service call should return True immediately
      assert result is True


class TestTiltConfirmation:
  """Test tilt confirmation with _wait_for_attribute when retry>0."""

  async def test_waits_for_tilt_confirmation_when_retry_specified(self, hass, mock_config_entry):
    """Test that _call_service waits for tilt confirmation when retry>0."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock _wait_for_attribute to return True (tilt reached)
    mock_wait_for_attribute = AsyncMock(return_value=True)

    with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
       patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):

      result = await mapped_cover._call_service(
        "set_cover_tilt_position",
        {"entity_id": "cover.test_cover", "tilt_position": 80},
        retry=3
      )

      # Assert _wait_for_attribute was called with correct parameters
      mock_wait_for_attribute.assert_called_once_with(
        "current_tilt_position", 80, timeout=30
      )

      # Service call should return True when tilt is reached
      assert result is True

  async def test_retries_on_tilt_confirmation_failure(self, hass, mock_config_entry):
    """Test that _call_service retries when tilt confirmation fails."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock _wait_for_attribute to always return False (tilt not reached)
    mock_wait_for_attribute = AsyncMock(return_value=False)

    with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
       patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()), \
       patch("asyncio.sleep", AsyncMock()):

      result = await mapped_cover._call_service(
        "set_cover_tilt_position",
        {"entity_id": "cover.test_cover", "tilt_position": 80},
        retry=2
      )

      # Should be called 1 + retry (3) times
      assert mock_wait_for_attribute.call_count == 3

      # Service call should return False after all retries fail
      assert result is False

  async def test_no_wait_for_tilt_when_retry_zero(self, hass, mock_config_entry):
    """Test that _call_service doesn't wait for tilt confirmation when retry=0."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock _wait_for_attribute to track if it's called
    mock_wait_for_attribute = AsyncMock(return_value=True)

    with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
       patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):

      result = await mapped_cover._call_service(
        "set_cover_tilt_position",
        {"entity_id": "cover.test_cover", "tilt_position": 80},
        retry=0  # No retries
      )

      # _wait_for_attribute should not be called
      mock_wait_for_attribute.assert_not_called()

      # Service call should return True immediately
      assert result is True


class TestAbortLogic:
  """Test abort_check functionality in _call_service."""

  async def test_aborts_service_call_when_check_returns_true(self, hass, mock_config_entry):
    """Test that service call is aborted when abort_check returns True."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock service call and abort_check function that returns True
    mock_async_call = AsyncMock()
    abort_check = MagicMock(return_value=True)

    with patch("homeassistant.core.ServiceRegistry.async_call", mock_async_call):
      result = await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70},
        abort_check=abort_check
      )

      # Abort check should be called
      abort_check.assert_called_once()

      # Service call should not be made
      mock_async_call.assert_not_called()

      # Result should be False when aborted
      assert result is False

  async def test_continues_service_call_when_check_returns_false(self, hass, mock_config_entry):
    """Test that service call continues when abort_check returns False."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock service call and abort_check function that returns False
    mock_async_call = AsyncMock()
    abort_check = MagicMock(return_value=False)

    with patch("homeassistant.core.ServiceRegistry.async_call", mock_async_call):
      result = await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70},
        abort_check=abort_check
      )

      # Abort check should be called
      abort_check.assert_called_once()

      # Service call should be made
      mock_async_call.assert_called_once()

      # Result should be True
      assert result is True

  async def test_abort_check_called_on_each_retry(self, hass, mock_config_entry):
    """Test that abort_check is called on each retry attempt."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock _wait_for_attribute to return False to trigger retries
    mock_wait_for_attribute = AsyncMock(return_value=False)

    # Configure abort_check to return False for first call, True for second call
    abort_check = MagicMock(side_effect=[False, True])

    with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
       patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()), \
       patch("asyncio.sleep", AsyncMock()):

      result = await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70},
        retry=2,
        abort_check=abort_check
      )

      # Abort check should be called twice (once on first try, once after first retry)
      assert abort_check.call_count == 2

      # Service call should return False when aborted during retries
      assert result is False


class TestExceptionHandling:
  """Test exception handling and logging in _call_service."""

  async def test_handles_service_call_exceptions(self, hass, mock_config_entry, caplog):
    """Test that _call_service handles exceptions from service calls."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock service call to raise an exception
    mock_async_call = AsyncMock(side_effect=Exception("Test error"))

    with patch("homeassistant.core.ServiceRegistry.async_call", mock_async_call), \
       patch("asyncio.sleep", AsyncMock()), \
       caplog.at_level(logging.WARNING):

      result = await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70},
        retry=0  # No retries
      )

      # Service call should return False on exception
      assert result is False

      # Should log a warning
      assert "Exception on set_cover_position: Test error" in caplog.text

  async def test_retries_after_exception(self, hass, mock_config_entry):
    """Test that _call_service retries after an exception."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Configure service call to fail on first attempt, succeed on second
    mock_async_call = AsyncMock(side_effect=[Exception("Test error"), None])

    # Mock _wait_for_attribute to return True on second attempt
    mock_wait_for_attribute = AsyncMock(return_value=True)

    with patch("homeassistant.core.ServiceRegistry.async_call", mock_async_call), \
       patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
       patch("asyncio.sleep", AsyncMock()):

      result = await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70},
        retry=2
      )

      # Service call should be called twice (once fails, once succeeds)
      assert mock_async_call.call_count == 2

      # Result should be True since second attempt succeeds
      assert result is True

  async def test_logs_max_retries_reached(self, hass, mock_config_entry, caplog):
    """Test that _call_service logs when max retries are reached."""
    # Set up test cover
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

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock _wait_for_attribute to always fail
    mock_wait_for_attribute = AsyncMock(return_value=False)

    with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
       patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()), \
       patch("asyncio.sleep", AsyncMock()), \
       caplog.at_level(logging.WARNING):

      await mapped_cover._call_service(
        "set_cover_position",
        {"entity_id": "cover.test_cover", "position": 70},
        retry=2
      )

      # Should log a warning about max retries
      assert "Max retries (2) reached for set_cover_position" in caplog.text
