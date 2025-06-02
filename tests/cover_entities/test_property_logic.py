"""Test property logic for MappedCover."""
import pytest
import time
from unittest.mock import patch, MagicMock
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
