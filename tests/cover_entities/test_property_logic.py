"""Test property logic for MappedCover."""
import time
import pytest_check as check
from unittest.mock import patch, MagicMock, AsyncMock
from homeassistant.components.cover import CoverEntityFeature, CoverState
from custom_components.mappedcover.cover import MappedCover
from tests.helpers.mocks.throttler import MockThrottler
from tests.helpers import create_unified_test_environment

# Import helpers and fixtures
from tests.fixtures import *  # Import all shared fixtures
from tests.constants import FEATURES_WITH_TILT


class TestCurrentCoverPosition:
    """Test current_cover_position property logic."""

    async def test_returns_target_when_target_is_set(self, hass, full_mock_setup):
        """Test that current_cover_position returns target position when _target_position is set."""
        # Create test environment using our new comprehensive helper
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": FEATURES_WITH_TILT,
                "current_position": 0,
                "current_tilt_position": 0,
                "device_class": "blind"
            }
        )

        # Extract the entity from our environment
        mapped_cover = env["entity"]

        # Set a target position (source scale: 50)
        mapped_cover._target_position = 50

        # Current position should return remapped target (50 -> 50 in user scale)
        result = mapped_cover.current_cover_position
        check.equal(result, 50)  # 50 maps from source 50 with range 10-90

    async def test_returns_remapped_source_when_no_target(self, hass, mock_config_entry):
        """Test that current_cover_position returns remapped source position when no target."""
        # Create test environment with position 45
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="open",
            attributes={
                "supported_features": FEATURES_WITH_TILT,
                "current_position": 45,
                "current_tilt_position": 30,
                "device_class": "blind"
            }
        )

        # Extract the entity
        mapped_cover = env["entity"]

        # No target is set, should return remapped source position
        result = mapped_cover.current_cover_position
        # 45 in source range 10-90 maps to 44 in user range
        check.equal(result, 44)

    async def test_returns_none_when_source_unavailable(self, hass, mock_config_entry):
        """Test that current_cover_position returns None when source is unavailable."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="unavailable",
            attributes={}
        )
        mapped_cover = env["entity"]
        mapped_cover._target_position = None
        result = mapped_cover.current_cover_position
        check.is_none(result)

    async def test_returns_none_when_source_position_missing(self, hass, mock_config_entry):
        """Test that current_cover_position returns None when source position is missing."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="open",
            attributes={
                "supported_features": FEATURES_WITH_TILT,
                # Missing current_position
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._target_position = None
        result = mapped_cover.current_cover_position
        check.is_none(result)

    async def test_target_position_priority_over_source(self, hass, mock_config_entry):
        """Test that target position takes priority over source position."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="open",
            attributes={
                "supported_features": FEATURES_WITH_TILT,
                "current_position": 30,
                "current_tilt_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._target_position = 60
        result = mapped_cover.current_cover_position
        # 60 maps from source 60 with range 10-90 to user scale
        check.equal(result, 63)

# Additional tests will be migrated as we continue...


class TestCurrentCoverTiltPosition:
    """Test current_cover_tilt_position property logic."""

    async def test_returns_target_when_target_is_set(self, hass, full_mock_setup):
        """Test that current_cover_tilt_position returns target tilt when _target_tilt is set."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": FEATURES_WITH_TILT,
                "current_position": 0,
                "current_tilt_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._target_tilt = 50
        result = mapped_cover.current_cover_tilt_position
        check.equal(result, 50)

    async def test_returns_remapped_source_when_no_target(self, hass, mock_config_entry):
        """Test that current_cover_tilt_position returns remapped source tilt when no target."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="open",
            attributes={
                "supported_features": FEATURES_WITH_TILT,
                "current_position": 50,
                "current_tilt_position": 40,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._target_tilt = None
        result = mapped_cover.current_cover_tilt_position
        check.equal(result, 40)

    async def test_returns_none_when_source_tilt_missing(self, hass, mock_config_entry):
        """Test that current_cover_tilt_position returns None when source tilt is missing."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="open",
            attributes={
                "supported_features": FEATURES_WITH_TILT,
                "current_position": 50,
                # Missing current_tilt_position
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._target_tilt = None
        result = mapped_cover.current_cover_tilt_position
        check.is_none(result)

    async def test_target_tilt_priority_over_source(self, hass, mock_config_entry):
        """Test that target tilt takes priority over source tilt."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="open",
            attributes={
                "supported_features": FEATURES_WITH_TILT,
                "current_position": 50,
                "current_tilt_position": 25,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._target_tilt = 70
        result = mapped_cover.current_cover_tilt_position
        # 70 maps from source 70 with range 5-95 to user scale
        check.equal(result, 72)


class TestSupportedFeatures:
    """Test supported_features property logic."""

    async def test_masks_only_relevant_features(self, hass, mock_config_entry):
        """Test that supported_features only exposes relevant cover features."""
        all_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION |
            CoverEntityFeature.STOP | CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT |
            CoverEntityFeature.SET_TILT_POSITION | CoverEntityFeature.STOP_TILT |
            0x1000 | 0x2000
        )
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": all_features,
                "current_position": 0,
                "current_tilt_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        result = mapped_cover.supported_features
        expected_mask = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION |
            CoverEntityFeature.STOP | CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT |
            CoverEntityFeature.SET_TILT_POSITION | CoverEntityFeature.STOP_TILT
        )
        check.equal(result, expected_mask)

    async def test_returns_zero_when_source_missing(self, hass, mock_config_entry):
        """Test that supported_features returns 0 when source entity is missing."""
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.nonexistent", MockThrottler())
        result = mapped_cover.supported_features
        check.equal(result, 0)

    async def test_handles_missing_features_attribute(self, hass, mock_config_entry):
        """Test that supported_features handles missing supported_features attribute gracefully."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "current_position": 0,
                "device_class": "blind"
                # Missing supported_features
            }
        )
        mapped_cover = env["entity"]
        result = mapped_cover.supported_features
        check.equal(result, 0)

    async def test_partial_feature_support(self, hass, mock_config_entry):
        """Test supported_features with partial feature support."""
        basic_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": basic_features,
                "current_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        result = mapped_cover.supported_features
        check.equal(result, basic_features)


class TestIsClosed:
    """Test is_closed property logic."""

    async def test_closed_when_position_zero_and_tilt_zero(self, hass, mock_config_entry):
        """Test that is_closed returns True when position=0 and tilt=0."""
        # First, min position/tilt (should not be closed)
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 10,  # Source min position
                "current_tilt_position": 5,  # Source min tilt
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        check.equal(mapped_cover.current_cover_position, 1)
        check.equal(mapped_cover.current_cover_tilt_position, 1)
        check.is_false(mapped_cover.is_closed)
        # Now, actually closed (0)
        env2 = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 0,
                "current_tilt_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover2 = env2["entity"]
        check.equal(mapped_cover2.current_cover_position, 0)
        check.equal(mapped_cover2.current_cover_tilt_position, 0)
        check.is_true(mapped_cover2.is_closed)

    async def test_closed_when_position_zero_and_tilt_none(self, hass, mock_config_entry):
        """Test that is_closed returns True when position=0 and tilt=None."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 15,  # No tilt support
                "current_position": 0,
                "device_class": "blind"
                # No current_tilt_position
            }
        )
        mapped_cover = env["entity"]
        check.equal(mapped_cover.current_cover_position, 0)
        check.is_none(mapped_cover.current_cover_tilt_position)
        check.is_true(mapped_cover.is_closed)

    async def test_not_closed_when_position_nonzero(self, hass, mock_config_entry):
        """Test that is_closed returns False when position is not 0."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="open",
            attributes={
                "supported_features": 143,
                "current_position": 50,  # Half open
                "current_tilt_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        check.not_equal(mapped_cover.current_cover_position, 0)
        check.equal(mapped_cover.current_cover_tilt_position, 0)
        check.is_false(mapped_cover.is_closed)

    async def test_not_closed_when_tilt_nonzero(self, hass, mock_config_entry):
        """Test that is_closed returns False when tilt is not 0 or None."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 0,
                "current_tilt_position": 30,  # Tilt open
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        check.equal(mapped_cover.current_cover_position, 0)
        check.not_equal(mapped_cover.current_cover_tilt_position, 0)
        check.is_false(mapped_cover.is_closed)


class TestIsClosingIsOpening:
    """Test is_closing and is_opening property logic."""

    async def test_is_closing_when_target_less_than_current(self, hass, mock_config_entry):
        """Test that is_closing returns True when target position < current position."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closing",
            attributes={
                "supported_features": 143,
                "current_position": 70,
                "current_tilt_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._target_position = 30
        check.is_true(mapped_cover.is_closing)
        check.is_false(mapped_cover.is_opening)

    async def test_is_opening_when_target_greater_than_current(self, hass, mock_config_entry):
        """Test that is_opening returns True when target position > current position."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="opening",
            attributes={
                "supported_features": 143,
                "current_position": 30,
                "current_tilt_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._target_position = 70
        check.is_true(mapped_cover.is_opening)
        check.is_false(mapped_cover.is_closing)

    async def test_falls_back_to_super_when_no_target_or_position(self, hass, mock_config_entry):
        """Test that is_closing/is_opening fall back to super() when target or position is None."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closing",
            attributes={
                "supported_features": 143,
                "device_class": "blind"
                # No current_position
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._target_position = None
        check.is_false(mapped_cover.is_closing)
        check.is_false(mapped_cover.is_opening)


class TestDeviceClass:
    """Test device_class property logic."""

    async def test_reflects_source_device_class(self, hass, mock_config_entry):
        """Test that device_class reflects the underlying cover's device_class."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 0,
                "device_class": "shutter"
            }
        )
        mapped_cover = env["entity"]
        check.equal(mapped_cover.device_class, "shutter")

    async def test_returns_none_when_source_missing_device_class(self, hass, mock_config_entry):
        """Test that device_class returns None when source has no device_class."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 0
                # No device_class attribute
            }
        )
        mapped_cover = env["entity"]
        check.is_none(mapped_cover.device_class)

    async def test_returns_none_when_source_unavailable(self, hass, mock_config_entry):
        """Test that device_class returns None when source entity is unavailable."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="unavailable",
            attributes={}
        )
        mapped_cover = env["entity"]
        check.is_none(mapped_cover.device_class)


class TestIsMoving:
    """Test is_moving property logic."""

    async def test_is_moving_when_recently_commanded(self, hass, mock_config_entry, mock_source_cover_state):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._last_position_command = time.time()
        check.is_true(mapped_cover.is_moving)

    async def test_is_moving_when_source_state_opening(self, hass, mock_config_entry):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state=CoverState.OPENING,
            attributes={
                "supported_features": 143,
                "current_position": 50,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._last_position_command = 0
        check.is_true(mapped_cover.is_moving)

    async def test_is_moving_when_source_state_closing(self, hass, mock_config_entry):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state=CoverState.CLOSING,
            attributes={
                "supported_features": 143,
                "current_position": 50,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._last_position_command = 0
        check.is_true(mapped_cover.is_moving)

    async def test_not_moving_when_static_and_no_recent_command(self, hass, mock_config_entry):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state=CoverState.OPEN,
            attributes={
                "supported_features": 143,
                "current_position": 100,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._last_position_command = time.time() - 10
        check.is_false(mapped_cover.is_moving)

    async def test_not_moving_after_command_timeout(self, hass, mock_config_entry, mock_source_cover_state):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._last_position_command = time.time() - 6
        check.is_false(mapped_cover.is_moving)

    async def test_is_moving_edge_case_source_missing(self, hass, mock_config_entry):
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.nonexistent", MockThrottler())
        mapped_cover._last_position_command = 0
        check.is_false(mapped_cover.is_moving)

    async def test_position_command_updates_last_position_command(self, hass, mock_config_entry, mock_source_cover_state):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            initial_time = mapped_cover._last_position_command
            await mapped_cover._call_service("set_cover_position", {"position": 50})
            check.is_true(mapped_cover._last_position_command > initial_time)
            check.is_true(mapped_cover.is_moving)

    async def test_tilt_command_does_not_update_last_position_command(self, hass, mock_config_entry, mock_source_cover_state):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            initial_time = mapped_cover._last_position_command
            await mapped_cover._call_service("set_cover_tilt_position", {"tilt_position": 50})
            check.equal(mapped_cover._last_position_command, initial_time)

    async def test_is_moving_after_position_command_via_service(self, hass, mock_config_entry, mock_source_cover_state):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state=CoverState.OPEN,
            attributes={
                "supported_features": 143,
                "current_position": 50,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._last_position_command = time.time() - 10
        check.is_false(mapped_cover.is_moving)
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            await mapped_cover._call_service("set_cover_position", {"position": 75})
            check.is_true(mapped_cover.is_moving)

    async def test_is_moving_after_tilt_command_via_service(self, hass, mock_config_entry, mock_source_cover_state):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state=CoverState.OPEN,
            attributes={
                "supported_features": 143,
                "current_position": 50,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._last_position_command = time.time() - 10
        check.is_false(mapped_cover.is_moving)
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            await mapped_cover._call_service("set_cover_tilt_position", {"tilt_position": 45})
            check.is_false(mapped_cover.is_moving)

    async def test_multiple_command_types_timestamp_behavior(self, hass, mock_config_entry, mock_source_cover_state):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            mapped_cover._last_position_command = time.time() - 10
            initial_time = mapped_cover._last_position_command
            await mapped_cover._call_service("set_cover_tilt_position", {"tilt_position": 30})
            check.equal(mapped_cover._last_position_command, initial_time)
            await mapped_cover._call_service("set_cover_position", {"position": 60})
            first_position_time = mapped_cover._last_position_command
            check.is_true(first_position_time > initial_time)
            await mapped_cover._call_service("set_cover_tilt_position", {"tilt_position": 70})
            check.equal(mapped_cover._last_position_command,
                        first_position_time)
            await mapped_cover._call_service("set_cover_position", {"position": 80})
            second_position_time = mapped_cover._last_position_command
            check.is_true(second_position_time > first_position_time)

    async def test_stop_commands_do_not_update_timestamp(self, hass, mock_config_entry, mock_source_cover_state):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            initial_time = mapped_cover._last_position_command
            await mapped_cover._call_service("stop_cover", {})
            check.equal(mapped_cover._last_position_command, initial_time)
            await mapped_cover._call_service("stop_cover_tilt", {})
            check.equal(mapped_cover._last_position_command, initial_time)


class TestPropertyIntegration:
    """Test property integration scenarios."""

    async def test_properties_with_target_positions_set(self, hass, mock_config_entry):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="opening",
            attributes={
                "supported_features": 143,
                "current_position": 40,
                "current_tilt_position": 30,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._target_position = 70
        mapped_cover._target_tilt = 60
        check.equal(mapped_cover.current_cover_position, 75)
        check.equal(mapped_cover.current_cover_tilt_position, 62)
        check.is_false(mapped_cover.is_closed)
        check.is_true(mapped_cover.is_opening)
        check.equal(mapped_cover.device_class, "blind")

    async def test_properties_after_target_cleared(self, hass, mock_config_entry):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="open",
            attributes={
                "supported_features": 143,
                "current_position": 70,
                "current_tilt_position": 60,
                "device_class": "blind"
            }
        )
        mapped_cover = env["entity"]
        mapped_cover._target_position = None
        mapped_cover._target_tilt = None
        check.equal(mapped_cover.current_cover_position, 75)
        check.equal(mapped_cover.current_cover_tilt_position, 62)
        check.is_false(mapped_cover.is_closed)
        check.is_false(mapped_cover.is_opening)
        check.is_false(mapped_cover.is_closing)

    async def test_properties_with_various_remapping_ranges(self, hass):
        config_entry = await create_mock_config_entry(
            hass,
            min_position=20,
            max_position=80,
            min_tilt_position=10,
            max_tilt_position=90
        )
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="open",
            attributes={
                "supported_features": 143,
                "current_position": 50,
                "current_tilt_position": 50,
                "device_class": "blind"
            },
            config_data={
                "min_position": 20,
                "max_position": 80,
                "min_tilt_position": 10,
                "max_tilt_position": 90
            }
        )
        mapped_cover = env["entity"]
        check.equal(mapped_cover.current_cover_position, 50)
        check.equal(mapped_cover.current_cover_tilt_position, 50)
        check.is_false(mapped_cover.is_closed)


class TestAvailability:
    """Test available property logic."""

    async def test_available_when_source_exists_and_available(self, hass, mock_config_entry):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="closed",
            attributes={
                "supported_features": 143,
                "current_position": 0
            }
        )
        mapped_cover = env["entity"]
        check.is_true(mapped_cover.available)

    async def test_unavailable_when_source_is_unavailable(self, hass, mock_config_entry):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="unavailable"
        )
        mapped_cover = env["entity"]
        check.is_false(mapped_cover.available)

    async def test_unavailable_when_source_is_unknown(self, hass, mock_config_entry):
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="unknown"
        )
        mapped_cover = env["entity"]
        check.is_false(mapped_cover.available)

    async def test_unavailable_when_source_missing(self, hass, mock_config_entry):
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.nonexistent", MockThrottler())
        check.is_false(mapped_cover.available)


class TestUniqueId:
    """Test unique_id property logic."""

    async def test_unique_id_format(self, hass, mock_config_entry):
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        expected_unique_id = f"{mock_config_entry.entry_id}_cover.test_cover"
        check.equal(mapped_cover.unique_id, expected_unique_id)

    async def test_unique_ids_are_distinct(self, hass, mock_config_entry):
        mapped_cover1 = MappedCover(
            hass, mock_config_entry, "cover.test_cover1", MockThrottler())
        mapped_cover2 = MappedCover(
            hass, mock_config_entry, "cover.test_cover2", MockThrottler())
        check.not_equal(mapped_cover1.unique_id, mapped_cover2.unique_id)
        check.equal(mapped_cover1.unique_id,
                    f"{mock_config_entry.entry_id}_cover.test_cover1")
        check.equal(mapped_cover2.unique_id,
                    f"{mock_config_entry.entry_id}_cover.test_cover2")

    async def test_unique_ids_with_different_config_entries(self, hass):
        config_entry1 = await create_mock_config_entry(hass)
        config_entry2 = await create_mock_config_entry(hass)
        mapped_cover1 = MappedCover(
            hass, config_entry1, "cover.test_cover", MockThrottler())
        mapped_cover2 = MappedCover(
            hass, config_entry2, "cover.test_cover", MockThrottler())
        check.not_equal(mapped_cover1.unique_id, mapped_cover2.unique_id)
        check.equal(mapped_cover1.unique_id,
                    f"{config_entry1.entry_id}_cover.test_cover")
        check.equal(mapped_cover2.unique_id,
                    f"{config_entry2.entry_id}_cover.test_cover")


class TestNameProperty:
    """Test name property logic."""

    async def test_name_with_default_pattern_device_name(self, hass, mock_config_entry):
        with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
                patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
                patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mock_entity = MagicMock()
            mock_entity.device_id = "device123"
            mock_ent_reg.return_value.async_get.return_value = mock_entity
            mock_device = MagicMock()
            mock_device.name = "Living Room Blinds"
            mock_dev_reg.return_value.async_get.return_value = mock_device
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        expected_name = "Mapped Living Room Blinds"
        check.equal(mapped_cover.name, expected_name)

    async def test_name_with_default_pattern_no_device(self, hass, mock_config_entry):
        with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
                patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
                patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mock_entity = MagicMock()
            mock_entity.device_id = None
            mock_ent_reg.return_value.async_get.return_value = mock_entity
            mock_dev_reg.return_value.async_get.return_value = None
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        expected_name = "Mapped cover.test_cover"
        check.equal(mapped_cover.name, expected_name)

    async def test_name_with_custom_pattern_partial_replacement(self, hass):
        config_entry = await create_mock_config_entry(
            hass,
            rename_pattern=r"^(.+) Blinds$",
            rename_replacement=r"Smart \1 Cover"
        )
        with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
                patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
                patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mock_entity = MagicMock()
            mock_entity.device_id = "device123"
            mock_ent_reg.return_value.async_get.return_value = mock_entity
            mock_device = MagicMock()
            mock_device.name = "Kitchen Blinds"
            mock_dev_reg.return_value.async_get.return_value = mock_device
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        expected_name = "Smart Kitchen Cover"
        check.equal(mapped_cover.name, expected_name)

    async def test_name_with_pattern_no_match(self, hass):
        config_entry = await create_mock_config_entry(
            hass,
            rename_pattern=r"^Window (.+)$",
            rename_replacement=r"Mapped \1"
        )
        with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
                patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
                patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mock_entity = MagicMock()
            mock_entity.device_id = "device123"
            mock_ent_reg.return_value.async_get.return_value = mock_entity
            mock_device = MagicMock()
            mock_device.name = "Kitchen Blinds"
            mock_dev_reg.return_value.async_get.return_value = mock_device
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        expected_name = "Kitchen Blinds"
        check.equal(mapped_cover.name, expected_name)

    async def test_name_with_complex_regex_groups(self, hass):
        config_entry = await create_mock_config_entry(
            hass,
            rename_pattern=r"^([A-Z][a-z]+) ([A-Z][a-z]+) (.+)$",
            rename_replacement=r"Virtual \3 in \1 \2"
        )
        with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
                patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
                patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mock_entity = MagicMock()
            mock_entity.device_id = "device123"
            mock_ent_reg.return_value.async_get.return_value = mock_entity
            mock_device = MagicMock()
            mock_device.name = "Master Bedroom Curtains"
            mock_dev_reg.return_value.async_get.return_value = mock_device
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        expected_name = "Virtual Curtains in Master Bedroom"
        check.equal(mapped_cover.name, expected_name)

    async def test_name_with_special_characters(self, hass):
        config_entry = await create_mock_config_entry(
            hass,
            rename_pattern=r"(.+)",
            rename_replacement=r"[\1] - Mapped"
        )
        with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
                patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
                patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mock_entity = MagicMock()
            mock_entity.device_id = "device123"
            mock_ent_reg.return_value.async_get.return_value = mock_entity
            mock_device = MagicMock()
            mock_device.name = "Café & Restaurant Awning"
            mock_dev_reg.return_value.async_get.return_value = mock_device
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        expected_name = "[Café & Restaurant Awning] - Mapped"
        check.equal(mapped_cover.name, expected_name)

    async def test_name_fallback_to_entity_id_various_scenarios(self, hass, mock_config_entry):
        with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
                patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
                patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mock_ent_reg.return_value.async_get.return_value = None
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.bathroom_shutter", MockThrottler())
            expected_name = "Mapped cover.bathroom_shutter"
            check.equal(mapped_cover.name, expected_name)
            mock_entity = MagicMock()
            mock_entity.device_id = None
            mock_ent_reg.return_value.async_get.return_value = mock_entity
            mock_dev_reg.return_value.async_get.return_value = None
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.bathroom_shutter", MockThrottler())
            check.equal(mapped_cover.name, expected_name)


class TestDeviceInfoProperty:
    """Test device_info property logic."""

    async def test_device_info_structure(self, hass, mock_config_entry):
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        device_info = mapped_cover.device_info
        check.is_instance(device_info, dict)
        check.is_in("identifiers", device_info)
        check.is_in("name", device_info)
        check.is_in("manufacturer", device_info)
        check.is_in("model", device_info)

    async def test_device_info_identifiers_format(self, hass, mock_config_entry):
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        device_info = mapped_cover.device_info
        expected_identifiers = {("mappedcover", mapped_cover.unique_id)}
        check.equal(device_info["identifiers"], expected_identifiers)

    async def test_device_info_name_matches_entity_name(self, hass, mock_config_entry):
        with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
                patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
                patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mock_entity = MagicMock()
            mock_entity.device_id = "device123"
            mock_ent_reg.return_value.async_get.return_value = mock_entity
            mock_device = MagicMock()
            mock_device.name = "Living Room Blinds"
            mock_dev_reg.return_value.async_get.return_value = mock_device
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        device_info = mapped_cover.device_info
        check.equal(device_info["name"], mapped_cover.name)
        check.equal(device_info["name"], "Mapped Living Room Blinds")

    async def test_device_info_manufacturer_and_model(self, hass, mock_config_entry):
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        device_info = mapped_cover.device_info
        check.equal(device_info["manufacturer"], "Mapped Cover Integration")
        check.equal(device_info["model"], "Virtual Cover")

    async def test_device_info_consistency_across_calls(self, hass, mock_config_entry):
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        device_info1 = mapped_cover.device_info
        device_info2 = mapped_cover.device_info
        check.equal(device_info1, device_info2)
        check.is_false(device_info1 is device_info2)

    async def test_device_info_with_custom_name_pattern(self, hass):
        config_entry = await create_mock_config_entry(
            hass,
            rename_pattern=r"^(.+) Blinds$",
            rename_replacement=r"Smart \1 Cover"
        )
        with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_ent_reg, \
                patch("custom_components.mappedcover.cover.device_registry.async_get") as mock_dev_reg, \
                patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mock_entity = MagicMock()
            mock_entity.device_id = "device123"
            mock_ent_reg.return_value.async_get.return_value = mock_entity
            mock_device = MagicMock()
            mock_device.name = "Kitchen Blinds"
            mock_dev_reg.return_value.async_get.return_value = mock_device
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        device_info = mapped_cover.device_info
        check.equal(device_info["name"], "Smart Kitchen Cover")
        check.equal(device_info["name"], mapped_cover.name)

    async def test_device_info_unique_identifiers_for_different_covers(self, hass, mock_config_entry):
        mapped_cover1 = MappedCover(
            hass, mock_config_entry, "cover.test_cover1", MockThrottler())
        mapped_cover2 = MappedCover(
            hass, mock_config_entry, "cover.test_cover2", MockThrottler())
        device_info1 = mapped_cover1.device_info
        device_info2 = mapped_cover2.device_info
        check.not_equal(device_info1["identifiers"],
                        device_info2["identifiers"])
        expected_id1 = {("mappedcover", mapped_cover1.unique_id)}
        expected_id2 = {("mappedcover", mapped_cover2.unique_id)}
        check.equal(device_info1["identifiers"], expected_id1)
        check.equal(device_info2["identifiers"], expected_id2)

    async def test_device_info_integration_grouping(self, hass, mock_config_entry):
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        device_info = mapped_cover.device_info
        identifiers = device_info["identifiers"]
        check.equal(len(identifiers), 1)
        domain, unique_id = next(iter(identifiers))
        check.equal(domain, "mappedcover")
        check.equal(unique_id, mapped_cover.unique_id)
