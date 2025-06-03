"""Test property logic for MappedCover."""
import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
from homeassistant.components.cover import CoverEntityFeature, CoverState
from custom_components.mappedcover.cover import MappedCover, RemapDirection

from tests.fixtures import *  # Import all shared fixtures
from tests.helpers import MockThrottler


class TestCurrentCoverPosition:
  """Test current_cover_position property logic."""

  async def test_returns_target_when_target_is_set(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that current_cover_position returns target position when _target_position is set."""
    # Create mapped cover with range 10-90
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set a target position (source scale: 50)
    mapped_cover._target_position = 50

    # Current position should return remapped target (50 -> ~50 in user scale)
    result = mapped_cover.current_cover_position
    assert result == 50  # 50 maps from source 50 with range 10-90

  async def test_returns_remapped_source_when_no_target(self, hass, mock_config_entry):
    """Test that current_cover_position returns remapped source position when no target."""
    # Set source cover to position 45 (mid-range in source scale)
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

    # No target position set
    mapped_cover._target_position = None

    # Should return remapped source position (45 from range 10-90 -> ~44 in user scale)
    result = mapped_cover.current_cover_position
    assert result == 44  # 45 maps from source to user scale with range 10-90

  async def test_returns_none_when_source_unavailable(self, hass, mock_config_entry):
    """Test that current_cover_position returns None when source is unavailable."""
    # Set source cover to unavailable
    hass.states.async_set("cover.test_cover", "unavailable", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    mapped_cover._target_position = None

    # Should return None when source is unavailable
    result = mapped_cover.current_cover_position
    assert result is None

  async def test_returns_none_when_source_position_missing(self, hass, mock_config_entry):
    """Test that current_cover_position returns None when source position is missing."""
    # Set source cover without current_position attribute
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "device_class": "blind"
        # Missing current_position
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    mapped_cover._target_position = None

    # Should return None when position attribute is missing
    result = mapped_cover.current_cover_position
    assert result is None

  async def test_target_position_priority_over_source(self, hass, mock_config_entry):
    """Test that target position takes priority over source position."""
    # Set source cover to position 30
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

    # Set target position to different value
    mapped_cover._target_position = 60

    # Should return target, not source
    result = mapped_cover.current_cover_position
    assert result == 63  # 60 maps from source 60 with range 10-90 to user scale


class TestCurrentCoverTiltPosition:
  """Test current_cover_tilt_position property logic."""

  async def test_returns_target_when_target_is_set(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that current_cover_tilt_position returns target tilt when _target_tilt is set."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set a target tilt position (source scale: 50)
    mapped_cover._target_tilt = 50

    # Current tilt should return remapped target
    result = mapped_cover.current_cover_tilt_position
    assert result == 50  # 50 maps from source 50 with range 5-95 to user scale

  async def test_returns_remapped_source_when_no_target(self, hass, mock_config_entry):
    """Test that current_cover_tilt_position returns remapped source tilt when no target."""
    # Set source cover with tilt position 40
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

    # No target tilt set
    mapped_cover._target_tilt = None

    # Should return remapped source tilt
    result = mapped_cover.current_cover_tilt_position
    assert result == 40  # 40 maps from source to user scale with range 5-95

  async def test_returns_none_when_source_tilt_missing(self, hass, mock_config_entry):
    """Test that current_cover_tilt_position returns None when source tilt is missing."""
    # Set source cover without current_tilt_position
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,
        "device_class": "blind"
        # Missing current_tilt_position
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    mapped_cover._target_tilt = None

    # Should return None when tilt attribute is missing
    result = mapped_cover.current_cover_tilt_position
    assert result is None

  async def test_target_tilt_priority_over_source(self, hass, mock_config_entry):
    """Test that target tilt takes priority over source tilt."""
    # Set source cover with tilt position 25
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

    # Set target tilt to different value
    mapped_cover._target_tilt = 70

    # Should return target, not source
    result = mapped_cover.current_cover_tilt_position
    assert result == 72  # 70 maps from source 70 with range 5-95 to user scale


class TestSupportedFeatures:
  """Test supported_features property logic."""

  async def test_masks_only_relevant_features(self, hass, mock_config_entry):
    """Test that supported_features only exposes relevant cover features."""
    # Set source cover with all possible features
    all_features = (
      CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION |
      CoverEntityFeature.STOP | CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT |
      CoverEntityFeature.SET_TILT_POSITION | CoverEntityFeature.STOP_TILT |
      # Add some non-cover features that should be filtered out
      0x1000 | 0x2000  # Fake features
    )

    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": all_features,
        "current_position": 0,
        "current_tilt_position": 0,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    result = mapped_cover.supported_features

    # Should only contain relevant cover features
    expected_mask = (
      CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION |
      CoverEntityFeature.STOP | CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT |
      CoverEntityFeature.SET_TILT_POSITION | CoverEntityFeature.STOP_TILT
    )
    assert result == expected_mask

  async def test_returns_zero_when_source_missing(self, hass, mock_config_entry):
    """Test that supported_features returns 0 when source entity is missing."""
    # Don't create any source entity
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.nonexistent", MockThrottler())

    result = mapped_cover.supported_features
    assert result == 0

  async def test_handles_missing_features_attribute(self, hass, mock_config_entry):
    """Test that supported_features handles missing supported_features attribute gracefully."""
    # Set source cover without supported_features attribute
    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "current_position": 0,
        "device_class": "blind"
        # Missing supported_features
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    result = mapped_cover.supported_features
    assert result == 0

  async def test_partial_feature_support(self, hass, mock_config_entry):
    """Test supported_features with partial feature support."""
    # Set source cover with only basic features (no tilt)
    basic_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION

    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": basic_features,
        "current_position": 0,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    result = mapped_cover.supported_features
    assert result == basic_features


class TestIsClosed:
  """Test is_closed property logic."""

  async def test_closed_when_position_zero_and_tilt_zero(self, hass, mock_config_entry):
    """Test that is_closed returns True when position=0 and tilt=0."""
    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": 143,
        "current_position": 10,  # Source min position
        "current_tilt_position": 5,  # Source min tilt
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Both position and tilt should map to 0 (fully closed)
    assert mapped_cover.current_cover_position == 1  # Min position maps to 1
    assert mapped_cover.current_cover_tilt_position == 1  # Min tilt maps to 1
    assert not mapped_cover.is_closed  # Not closed since position is 1

    # Set to actual closed position (0 in source scale)
    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": 143,
        "current_position": 0,  # Actually closed
        "current_tilt_position": 0,  # Actually closed
        "device_class": "blind"
      }
    )

    assert mapped_cover.current_cover_position == 0
    assert mapped_cover.current_cover_tilt_position == 0
    assert mapped_cover.is_closed

  async def test_closed_when_position_zero_and_tilt_none(self, hass, mock_config_entry):
    """Test that is_closed returns True when position=0 and tilt=None."""
    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": 15,  # No tilt support
        "current_position": 0,
        "device_class": "blind"
        # No current_tilt_position
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover.current_cover_position == 0
    assert mapped_cover.current_cover_tilt_position is None
    assert mapped_cover.is_closed

  async def test_not_closed_when_position_nonzero(self, hass, mock_config_entry):
    """Test that is_closed returns False when position is not 0."""
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,  # Half open
        "current_tilt_position": 0,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover.current_cover_position != 0
    assert mapped_cover.current_cover_tilt_position == 0
    assert not mapped_cover.is_closed

  async def test_not_closed_when_tilt_nonzero(self, hass, mock_config_entry):
    """Test that is_closed returns False when tilt is not 0 or None."""
    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": 143,
        "current_position": 0,
        "current_tilt_position": 30,  # Tilt open
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover.current_cover_position == 0
    assert mapped_cover.current_cover_tilt_position != 0
    assert not mapped_cover.is_closed


class TestIsClosingIsOpening:
  """Test is_closing and is_opening property logic."""

  async def test_is_closing_when_target_less_than_current(self, hass, mock_config_entry):
    """Test that is_closing returns True when target position < current position."""
    # Set source cover at position 70
    hass.states.async_set(
      "cover.test_cover",
      "closing",
      {
        "supported_features": 143,
        "current_position": 70,
        "current_tilt_position": 0,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set target to close (lower position)
    mapped_cover._target_position = 30

    assert mapped_cover.is_closing
    assert not mapped_cover.is_opening

  async def test_is_opening_when_target_greater_than_current(self, hass, mock_config_entry):
    """Test that is_opening returns True when target position > current position."""
    # Set source cover at position 30
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

    # Set target to open (higher position)
    mapped_cover._target_position = 70

    assert mapped_cover.is_opening
    assert not mapped_cover.is_closing

  async def test_falls_back_to_super_when_no_target_or_position(self, hass, mock_config_entry):
    """Test that is_closing/is_opening fall back to super() when target or position is None."""
    # Set source cover without position
    hass.states.async_set(
      "cover.test_cover",
      "closing",
      {
        "supported_features": 143,
        "device_class": "blind"
        # No current_position
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # No target set
    mapped_cover._target_position = None

    # Should fall back to super().is_closing (which is False by default)
    assert not mapped_cover.is_closing
    assert not mapped_cover.is_opening


class TestDeviceClass:
  """Test device_class property logic."""

  async def test_reflects_source_device_class(self, hass, mock_config_entry):
    """Test that device_class reflects the underlying cover's device_class."""
    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": 143,
        "current_position": 0,
        "device_class": "shutter"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover.device_class == "shutter"

  async def test_returns_none_when_source_missing_device_class(self, hass, mock_config_entry):
    """Test that device_class returns None when source has no device_class."""
    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": 143,
        "current_position": 0
        # No device_class attribute
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover.device_class is None

  async def test_returns_none_when_source_unavailable(self, hass, mock_config_entry):
    """Test that device_class returns None when source entity is unavailable."""
    hass.states.async_set("cover.test_cover", "unavailable", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover.device_class is None


class TestIsMoving:
  """Test is_moving property logic."""

  async def test_is_moving_when_recently_commanded(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that is_moving returns True when a position command was sent recently."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Simulate recent position command
    mapped_cover._last_position_command = time.time()

    assert mapped_cover.is_moving

  async def test_is_moving_when_source_state_opening(self, hass, mock_config_entry):
    """Test that is_moving returns True when source cover state is opening."""
    # Set source cover state to opening
    hass.states.async_set(
      "cover.test_cover",
      CoverState.OPENING,
      {
        "supported_features": 143,
        "current_position": 50,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # No recent command
    mapped_cover._last_position_command = 0

    assert mapped_cover.is_moving

  async def test_is_moving_when_source_state_closing(self, hass, mock_config_entry):
    """Test that is_moving returns True when source cover state is closing."""
    # Set source cover state to closing
    hass.states.async_set(
      "cover.test_cover",
      CoverState.CLOSING,
      {
        "supported_features": 143,
        "current_position": 50,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # No recent command
    mapped_cover._last_position_command = 0

    assert mapped_cover.is_moving

  async def test_not_moving_when_static_and_no_recent_command(self, hass, mock_config_entry):
    """Test that is_moving returns False when cover is static and no recent commands."""
    # Set source cover to static state
    hass.states.async_set(
      "cover.test_cover",
      CoverState.OPEN,
      {
        "supported_features": 143,
        "current_position": 100,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # No recent command (old timestamp)
    mapped_cover._last_position_command = time.time() - 10

    assert not mapped_cover.is_moving

  async def test_not_moving_after_command_timeout(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that is_moving returns False after command timeout (5 seconds)."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Simulate old position command (more than 5 seconds ago)
    mapped_cover._last_position_command = time.time() - 6

    assert not mapped_cover.is_moving

  async def test_is_moving_edge_case_source_missing(self, hass, mock_config_entry):
    """Test that is_moving handles missing source entity gracefully."""
    # Don't create source entity
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.nonexistent", MockThrottler())

    # No recent command
    mapped_cover._last_position_command = 0

    # Should not crash and return False
    assert not mapped_cover.is_moving

  async def test_position_command_updates_last_position_command(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that position commands update _last_position_command timestamp."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock service call to avoid actual call
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_call:
      # Record initial timestamp
      initial_time = mapped_cover._last_position_command

      # Call _call_service with position command
      await mapped_cover._call_service("set_cover_position", {"position": 50})

      # Timestamp should be updated
      assert mapped_cover._last_position_command > initial_time
      assert mapped_cover.is_moving  # Should be moving due to recent command

  async def test_tilt_command_does_not_update_last_position_command(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that tilt commands do NOT update _last_position_command timestamp."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock service call to avoid actual call
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_call:
      # Record initial timestamp
      initial_time = mapped_cover._last_position_command

      # Call _call_service with tilt command
      await mapped_cover._call_service("set_cover_tilt_position", {"tilt_position": 50})

      # Timestamp should NOT be updated (should remain the same)
      assert mapped_cover._last_position_command == initial_time

  async def test_is_moving_after_position_command_via_service(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that is_moving returns True after calling position command via _call_service."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set static source state
    hass.states.async_set(
      "cover.test_cover",
      CoverState.OPEN,
      {
        "supported_features": 143,
        "current_position": 50,
        "device_class": "blind"
      }
    )

    # Initially not moving (old timestamp)
    mapped_cover._last_position_command = time.time() - 10
    assert not mapped_cover.is_moving

    # Mock service call to avoid actual call
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_call:
      # Call position command via _call_service
      await mapped_cover._call_service("set_cover_position", {"position": 75})

      # Should now be moving due to recent command
      assert mapped_cover.is_moving

  async def test_is_moving_after_tilt_command_via_service(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that is_moving behavior after tilt command depends only on source state, not timestamp."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set static source state
    hass.states.async_set(
      "cover.test_cover",
      CoverState.OPEN,
      {
        "supported_features": 143,
        "current_position": 50,
        "device_class": "blind"
      }
    )

    # Set old timestamp so is_moving would be False due to timeout
    mapped_cover._last_position_command = time.time() - 10
    assert not mapped_cover.is_moving

    # Mock service call to avoid actual call
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_call:
      # Call tilt command via _call_service
      await mapped_cover._call_service("set_cover_tilt_position", {"tilt_position": 45})

      # Should still not be moving since:
      # 1. Tilt command doesn't update _last_position_command
      # 2. Source state is static (OPEN)
      assert not mapped_cover.is_moving

  async def test_multiple_command_types_timestamp_behavior(self, hass, mock_config_entry, mock_source_cover_state):
    """Test timestamp behavior with sequence of position and tilt commands."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock service call to avoid actual call
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_call:
      # Start with old timestamp
      mapped_cover._last_position_command = time.time() - 10
      initial_time = mapped_cover._last_position_command

      # Tilt command should not update timestamp
      await mapped_cover._call_service("set_cover_tilt_position", {"tilt_position": 30})
      assert mapped_cover._last_position_command == initial_time

      # Position command should update timestamp
      await mapped_cover._call_service("set_cover_position", {"position": 60})
      first_position_time = mapped_cover._last_position_command
      assert first_position_time > initial_time

      # Another tilt command should not change the timestamp from position command
      await mapped_cover._call_service("set_cover_tilt_position", {"tilt_position": 70})
      assert mapped_cover._last_position_command == first_position_time

      # Another position command should update timestamp again
      await mapped_cover._call_service("set_cover_position", {"position": 80})
      second_position_time = mapped_cover._last_position_command
      assert second_position_time > first_position_time

  async def test_stop_commands_do_not_update_timestamp(self, hass, mock_config_entry, mock_source_cover_state):
    """Test that stop commands do not update _last_position_command timestamp."""
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Mock service call to avoid actual call
    with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_call:
      # Record initial timestamp
      initial_time = mapped_cover._last_position_command

      # Stop commands should not update timestamp
      await mapped_cover._call_service("stop_cover", {})
      assert mapped_cover._last_position_command == initial_time

      await mapped_cover._call_service("stop_cover_tilt", {})
      assert mapped_cover._last_position_command == initial_time


class TestPropertyIntegration:
  """Test property integration scenarios."""

  async def test_properties_with_target_positions_set(self, hass, mock_config_entry):
    """Test property behavior when both position and tilt targets are set."""
    # Set source cover with current positions
    hass.states.async_set(
      "cover.test_cover",
      "opening",
      {
        "supported_features": 143,
        "current_position": 40,
        "current_tilt_position": 30,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Set targets different from current positions
    mapped_cover._target_position = 70
    mapped_cover._target_tilt = 60

    # Properties should reflect targets while moving
    assert mapped_cover.current_cover_position == 75  # Target 70 mapped to user scale
    assert mapped_cover.current_cover_tilt_position == 62  # Target 60 mapped to user scale
    assert not mapped_cover.is_closed  # Not closed
    assert mapped_cover.is_opening  # Target > current
    assert mapped_cover.device_class == "blind"

  async def test_properties_after_target_cleared(self, hass, mock_config_entry):
    """Test property behavior after targets are cleared (normal operation)."""
    # Set source cover with final positions
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 70,
        "current_tilt_position": 60,
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Clear targets (normal state after movement completes)
    mapped_cover._target_position = None
    mapped_cover._target_tilt = None

    # Properties should reflect actual source positions
    assert mapped_cover.current_cover_position == 75  # Source 70 mapped to user scale
    assert mapped_cover.current_cover_tilt_position == 62  # Source 60 mapped to user scale
    assert not mapped_cover.is_closed
    assert not mapped_cover.is_opening
    assert not mapped_cover.is_closing

  async def test_properties_with_various_remapping_ranges(self, hass):
    """Test properties with different remapping ranges."""
    # Create config with narrow ranges
    config_entry = await create_mock_config_entry(
      hass,
      min_position=20,
      max_position=80,
      min_tilt_position=10,
      max_tilt_position=90
    )

    # Set source cover at mid-range positions
    hass.states.async_set(
      "cover.test_cover",
      "open",
      {
        "supported_features": 143,
        "current_position": 50,  # Mid-range
        "current_tilt_position": 50,  # Mid-range
        "device_class": "blind"
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    # Properties should reflect the custom ranges
    assert mapped_cover.current_cover_position == 50  # 50 should map to ~50 in user scale
    assert mapped_cover.current_cover_tilt_position == 50  # 50 should map to ~50 in user scale
    assert not mapped_cover.is_closed


class TestAvailability:
  """Test available property logic."""

  async def test_available_when_source_exists_and_available(self, hass, mock_config_entry):
    """Test that available returns True when source exists and is available."""
    # Set source cover to an available state
    hass.states.async_set(
      "cover.test_cover",
      "closed",
      {
        "supported_features": 143,
        "current_position": 0
      }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Should return True when source exists and is not unavailable/unknown
    assert mapped_cover.available is True

  async def test_unavailable_when_source_is_unavailable(self, hass, mock_config_entry):
    """Test that available returns False when source is unavailable."""
    # Set source cover to unavailable
    hass.states.async_set("cover.test_cover", "unavailable")

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Should return False when source is unavailable
    assert mapped_cover.available is False

  async def test_unavailable_when_source_is_unknown(self, hass, mock_config_entry):
    """Test that available returns False when source is unknown."""
    # Set source cover to unknown
    hass.states.async_set("cover.test_cover", "unknown")

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Should return False when source is unknown
    assert mapped_cover.available is False

  async def test_unavailable_when_source_missing(self, hass, mock_config_entry):
    """Test that available returns False when source entity doesn't exist."""
    # Don't create source entity
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.nonexistent", MockThrottler())

    # Should return False when source doesn't exist
    assert mapped_cover.available is False


class TestUniqueId:
  """Test unique_id property logic."""

  async def test_unique_id_format(self, hass, mock_config_entry):
    """Test that unique_id follows the expected format."""
    # Create mapped cover
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Check unique_id format: entry_id_source_entity_id
    expected_unique_id = f"{mock_config_entry.entry_id}_cover.test_cover"
    assert mapped_cover.unique_id == expected_unique_id

  async def test_unique_ids_are_distinct(self, hass, mock_config_entry):
    """Test that unique_ids are distinct for different source entities."""
    # Create two mapped covers with different source entities
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover1 = MappedCover(hass, mock_config_entry, "cover.test_cover1", MockThrottler())
      mapped_cover2 = MappedCover(hass, mock_config_entry, "cover.test_cover2", MockThrottler())

    # Unique IDs should be different
    assert mapped_cover1.unique_id != mapped_cover2.unique_id
    assert mapped_cover1.unique_id == f"{mock_config_entry.entry_id}_cover.test_cover1"
    assert mapped_cover2.unique_id == f"{mock_config_entry.entry_id}_cover.test_cover2"

  async def test_unique_ids_with_different_config_entries(self, hass):
    """Test that unique_ids are distinct for different config entries."""
    # Create two config entries
    config_entry1 = await create_mock_config_entry(hass)
    config_entry2 = await create_mock_config_entry(hass)

    # Create mapped covers with same source but different config entries
    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover1 = MappedCover(hass, config_entry1, "cover.test_cover", MockThrottler())
      mapped_cover2 = MappedCover(hass, config_entry2, "cover.test_cover", MockThrottler())

    # Unique IDs should be different due to different config entries
    assert mapped_cover1.unique_id != mapped_cover2.unique_id

    # Verify the format follows the expected pattern: entry_id_source_entity_id
    assert mapped_cover1.unique_id == f"{config_entry1.entry_id}_cover.test_cover"
    assert mapped_cover2.unique_id == f"{config_entry2.entry_id}_cover.test_cover"


class TestNameProperty:
  """Test name property logic."""

  async def test_name_with_default_pattern_device_name(self, hass, mock_config_entry):
    """Test name property with default pattern using device name."""
    # Create source entity with device
    hass.states.async_set("cover.test_cover", "closed", {})

    # Mock device registry to return a device with name
    with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
         patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
         patch("custom_components.mappedcover.cover.Throttler", MockThrottler):

      # Mock entity registry entry
      mock_entity = MagicMock()
      mock_entity.device_id = "device123"
      mock_ent_reg.return_value.async_get.return_value = mock_entity

      # Mock device registry entry
      mock_device = MagicMock()
      mock_device.name = "Living Room Blinds"
      mock_dev_reg.return_value.async_get.return_value = mock_device

      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Default pattern "^.*$" with replacement "Mapped \g<0>" should prepend "Mapped "
    expected_name = "Mapped Living Room Blinds"
    assert mapped_cover.name == expected_name

  async def test_name_with_default_pattern_no_device(self, hass, mock_config_entry):
    """Test name property with default pattern when no device exists."""
    # Create source entity without device
    hass.states.async_set("cover.test_cover", "closed", {})

    # Mock registries to return no device
    with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
         patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
         patch("custom_components.mappedcover.cover.Throttler", MockThrottler):

      # Mock entity registry entry with no device
      mock_entity = MagicMock()
      mock_entity.device_id = None
      mock_ent_reg.return_value.async_get.return_value = mock_entity
      mock_dev_reg.return_value.async_get.return_value = None

      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Should use source entity ID with default pattern
    expected_name = "Mapped cover.test_cover"
    assert mapped_cover.name == expected_name

  async def test_name_with_custom_pattern_partial_replacement(self, hass):
    """Test name property with custom pattern for partial replacement."""
    # Create config with custom rename pattern
    config_entry = await create_mock_config_entry(
      hass,
      rename_pattern=r"^(.+) Blinds$",
      rename_replacement=r"Smart \1 Cover"
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
         patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
         patch("custom_components.mappedcover.cover.Throttler", MockThrottler):

      mock_entity = MagicMock()
      mock_entity.device_id = "device123"
      mock_ent_reg.return_value.async_get.return_value = mock_entity

      mock_device = MagicMock()
      mock_device.name = "Kitchen Blinds"
      mock_dev_reg.return_value.async_get.return_value = mock_device

      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    # Pattern should extract "Kitchen" and replace with "Smart Kitchen Cover"
    expected_name = "Smart Kitchen Cover"
    assert mapped_cover.name == expected_name

  async def test_name_with_pattern_no_match(self, hass):
    """Test name property when pattern doesn't match."""
    # Create config with pattern that won't match
    config_entry = await create_mock_config_entry(
      hass,
      rename_pattern=r"^Window (.+)$",
      rename_replacement=r"Mapped \1"
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
         patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
         patch("custom_components.mappedcover.cover.Throttler", MockThrottler):

      mock_entity = MagicMock()
      mock_entity.device_id = "device123"
      mock_ent_reg.return_value.async_get.return_value = mock_entity

      mock_device = MagicMock()
      mock_device.name = "Kitchen Blinds"  # Doesn't match "Window" pattern
      mock_dev_reg.return_value.async_get.return_value = mock_device

      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    # When pattern doesn't match, name should remain unchanged
    expected_name = "Kitchen Blinds"
    assert mapped_cover.name == expected_name

  async def test_name_with_complex_regex_groups(self, hass):
    """Test name property with complex regex patterns and multiple groups."""
    # Create config with complex pattern
    config_entry = await create_mock_config_entry(
      hass,
      rename_pattern=r"^([A-Z][a-z]+) ([A-Z][a-z]+) (.+)$",
      rename_replacement=r"Virtual \3 in \1 \2"
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
         patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
         patch("custom_components.mappedcover.cover.Throttler", MockThrottler):

      mock_entity = MagicMock()
      mock_entity.device_id = "device123"
      mock_ent_reg.return_value.async_get.return_value = mock_entity

      mock_device = MagicMock()
      mock_device.name = "Master Bedroom Curtains"
      mock_dev_reg.return_value.async_get.return_value = mock_device

      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    # Pattern should extract groups and rearrange them
    expected_name = "Virtual Curtains in Master Bedroom"
    assert mapped_cover.name == expected_name

  async def test_name_with_special_characters(self, hass):
    """Test name property with special characters in names."""
    # Create config with pattern that handles special characters
    config_entry = await create_mock_config_entry(
      hass,
      rename_pattern=r"(.+)",
      rename_replacement=r"[\1] - Mapped"
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
         patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
         patch("custom_components.mappedcover.cover.Throttler", MockThrottler):

      mock_entity = MagicMock()
      mock_entity.device_id = "device123"
      mock_ent_reg.return_value.async_get.return_value = mock_entity

      mock_device = MagicMock()
      mock_device.name = "Café & Restaurant Awning"
      mock_dev_reg.return_value.async_get.return_value = mock_device

      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    # Should handle special characters properly
    expected_name = "[Café & Restaurant Awning] - Mapped"
    assert mapped_cover.name == expected_name

  async def test_name_fallback_to_entity_id_various_scenarios(self, hass, mock_config_entry):
    """Test name property fallback to entity ID in various scenarios."""
    hass.states.async_set("cover.bathroom_shutter", "closed", {})

    with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
         patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
         patch("custom_components.mappedcover.cover.Throttler", MockThrottler):

      # Test scenario 1: No entity registry entry
      mock_ent_reg.return_value.async_get.return_value = None
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.bathroom_shutter", MockThrottler())
      expected_name = "Mapped cover.bathroom_shutter"
      assert mapped_cover.name == expected_name

      # Test scenario 2: Entity exists but no device_id
      mock_entity = MagicMock()
      mock_entity.device_id = None
      mock_ent_reg.return_value.async_get.return_value = mock_entity
      mock_dev_reg.return_value.async_get.return_value = None

      mapped_cover = MappedCover(hass, mock_config_entry, "cover.bathroom_shutter", MockThrottler())
      expected_name = "Mapped cover.bathroom_shutter"
      assert mapped_cover.name == expected_name


class TestDeviceInfoProperty:
  """Test device_info property logic."""

  async def test_device_info_structure(self, hass, mock_config_entry):
    """Test that device_info returns correct structure and required fields."""
    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    device_info = mapped_cover.device_info

    # Check structure and required fields
    assert isinstance(device_info, dict)
    assert "identifiers" in device_info
    assert "name" in device_info
    assert "manufacturer" in device_info
    assert "model" in device_info

  async def test_device_info_identifiers_format(self, hass, mock_config_entry):
    """Test that device_info identifiers use correct format."""
    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    device_info = mapped_cover.device_info

    # Check identifiers format: {(domain, unique_id)}
    expected_identifiers = {("mappedcover", mapped_cover.unique_id)}
    assert device_info["identifiers"] == expected_identifiers

  async def test_device_info_name_matches_entity_name(self, hass, mock_config_entry):
    """Test that device_info name matches the entity name."""
    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
         patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
         patch("custom_components.mappedcover.cover.Throttler", MockThrottler):

      mock_entity = MagicMock()
      mock_entity.device_id = "device123"
      mock_ent_reg.return_value.async_get.return_value = mock_entity

      mock_device = MagicMock()
      mock_device.name = "Living Room Blinds"
      mock_dev_reg.return_value.async_get.return_value = mock_device

      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    device_info = mapped_cover.device_info

    # Device info name should match entity name
    assert device_info["name"] == mapped_cover.name
    assert device_info["name"] == "Mapped Living Room Blinds"

  async def test_device_info_manufacturer_and_model(self, hass, mock_config_entry):
    """Test that device_info has correct manufacturer and model."""
    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    device_info = mapped_cover.device_info

    # Check manufacturer and model values
    assert device_info["manufacturer"] == "Mapped Cover Integration"
    assert device_info["model"] == "Virtual Cover"

  async def test_device_info_consistency_across_calls(self, hass, mock_config_entry):
    """Test that device_info returns consistent values across multiple calls."""
    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    # Get device_info multiple times
    device_info1 = mapped_cover.device_info
    device_info2 = mapped_cover.device_info

    # Should return identical dictionaries
    assert device_info1 == device_info2
    assert device_info1 is not device_info2  # Different object instances

  async def test_device_info_with_custom_name_pattern(self, hass):
    """Test device_info name with custom rename pattern."""
    # Create config with custom pattern
    config_entry = await create_mock_config_entry(
      hass,
      rename_pattern=r"^(.+) Blinds$",
      rename_replacement=r"Smart \1 Cover"
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
         patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
         patch("custom_components.mappedcover.cover.Throttler", MockThrottler):

      mock_entity = MagicMock()
      mock_entity.device_id = "device123"
      mock_ent_reg.return_value.async_get.return_value = mock_entity

      mock_device = MagicMock()
      mock_device.name = "Kitchen Blinds"
      mock_dev_reg.return_value.async_get.return_value = mock_device

      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    device_info = mapped_cover.device_info

    # Device info name should reflect custom pattern result
    assert device_info["name"] == "Smart Kitchen Cover"
    assert device_info["name"] == mapped_cover.name

  async def test_device_info_unique_identifiers_for_different_covers(self, hass, mock_config_entry):
    """Test that device_info identifiers are unique for different covers."""
    hass.states.async_set("cover.test_cover1", "closed", {})
    hass.states.async_set("cover.test_cover2", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover1 = MappedCover(hass, mock_config_entry, "cover.test_cover1", MockThrottler())
      mapped_cover2 = MappedCover(hass, mock_config_entry, "cover.test_cover2", MockThrottler())

    device_info1 = mapped_cover1.device_info
    device_info2 = mapped_cover2.device_info

    # Identifiers should be different for different covers
    assert device_info1["identifiers"] != device_info2["identifiers"]

    # Each should use their respective unique_id
    expected_id1 = {("mappedcover", mapped_cover1.unique_id)}
    expected_id2 = {("mappedcover", mapped_cover2.unique_id)}
    assert device_info1["identifiers"] == expected_id1
    assert device_info2["identifiers"] == expected_id2

  async def test_device_info_integration_grouping(self, hass, mock_config_entry):
    """Test that device_info groups entities under the integration."""
    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", MockThrottler())

    device_info = mapped_cover.device_info

    # Check that the domain in identifiers matches the integration domain
    identifiers = device_info["identifiers"]
    assert len(identifiers) == 1
    domain, unique_id = next(iter(identifiers))
    assert domain == "mappedcover"
    assert unique_id == mapped_cover.unique_id
