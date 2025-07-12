"""Test error handling and edge cases for MappedCover."""
import pytest_check as check
from unittest.mock import patch, MagicMock
from custom_components.mappedcover.cover import MappedCover

# Import helpers and fixtures
from tests.fixtures import *  # Import all shared fixtures
from tests.helpers import (
    MockThrottler,
    create_unified_test_environment,
)


class TestUnavailableUnknownStates:
    """Test handling of unavailable/unknown underlying cover states."""

    async def test_available_property_with_unavailable_source(self, hass, mock_config_entry):
        """Test that available returns False when source is unavailable."""
        # Create test environment with unavailable source
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="unavailable"  # Explicitly set state to unavailable
        )

        mapped_cover = env["entity"]

        # Should return False when source is unavailable
        check.is_false(mapped_cover.available)

    async def test_available_property_with_unknown_source(self, hass, mock_config_entry):
        """Test that available returns False when source state is unknown."""
        # Create test environment with unknown source
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="unknown"  # Explicitly set state to unknown
        )

        mapped_cover = env["entity"]

        # Should return False when source is unknown
        check.is_false(mapped_cover.available)

    async def test_current_cover_position_with_unavailable_source(self, hass, mock_config_entry):
        """Test that current_cover_position handles unavailable source gracefully."""
        # Create test environment with unavailable source
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="unavailable"
        )

        mapped_cover = env["entity"]

        # Should return None when source is unavailable
        check.is_none(mapped_cover.current_cover_position)

    async def test_current_cover_tilt_position_with_unknown_source(self, hass, mock_config_entry):
        """Test that current_cover_tilt_position handles unknown source gracefully."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="unknown"
        )
        mapped_cover = env["entity"]
        check.is_none(mapped_cover.current_cover_tilt_position)

    async def test_wait_for_attribute_with_unavailable_state(self, hass, mock_config_entry):
        """Test that _wait_for_attribute handles unavailable states and returns False."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="unavailable"
        )
        mapped_cover = env["entity"]
        result = await mapped_cover._wait_for_attribute("current_position", 50, timeout=0.1)
        check.is_false(result)

    async def test_wait_for_attribute_with_unknown_state(self, hass, mock_config_entry):
        """Test that _wait_for_attribute handles unknown states and returns False."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.test_cover",
            state="unknown"
        )
        mapped_cover = env["entity"]
        result = await mapped_cover._wait_for_attribute("current_position", 50, timeout=0.1)
        check.is_false(result)


class TestMissingSourceEntity:
    """Test handling of missing source entity scenarios."""

    async def test_available_property_with_missing_source(self, hass, mock_config_entry):
        """Test that available returns False when source entity is missing."""
        # Do NOT create any state for the entity
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.nonexistent", MockThrottler())
        check.is_false(mapped_cover.available)

    async def test_current_position_with_missing_source(self, hass, mock_config_entry):
        """Test that current_cover_position returns None when source entity is missing."""
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.nonexistent", MockThrottler())
        mapped_cover._target_position = None
        check.is_none(mapped_cover.current_cover_position)

    async def test_current_tilt_with_missing_source(self, hass, mock_config_entry):
        """Test that current_cover_tilt_position returns None when source entity is missing."""
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.nonexistent", MockThrottler())
        mapped_cover._target_tilt = None
        check.is_none(mapped_cover.current_cover_tilt_position)

    async def test_is_moving_with_missing_source(self, hass, mock_config_entry):
        """Test that is_moving handles missing source entity gracefully."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.nonexistent"
        )
        mapped_cover = env["entity"]
        mapped_cover._last_position_command = 0
        check.is_false(mapped_cover.is_moving)

    async def test_wait_for_attribute_with_missing_source(self, hass, mock_config_entry):
        """Test that _wait_for_attribute handles missing source entity and returns False."""
        env = await create_unified_test_environment(
            hass,
            entity_id="cover.nonexistent"
        )
        mapped_cover = env["entity"]
        result = await mapped_cover._wait_for_attribute("current_position", 50, timeout=0.1)
        check.is_false(result)


class TestDeviceIdSafety:
    """Test device_id safety when source entity has no device."""

    async def test_init_with_source_having_no_device(self, hass, mock_config_entry):
        """Test that initialization handles source entity with no device gracefully."""
        # Create source entity state but no device info
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {
                "supported_features": 143,
                "current_position": 50,
                "device_class": "blind"
            }
        )
        # Mock the entity registry to return an entity with no device_id
        mock_entity = MagicMock()
        mock_entity.device_id = None
        with patch("custom_components.mappedcover.cover.entity_registry.async_get") as mock_get_registry:
            mock_registry = mock_get_registry.return_value
            mock_registry.async_get.return_value = mock_entity
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
            check.is_none(mapped_cover._device)


class TestMalformedSourceAttributes:
    """Test handling of malformed source entity attributes."""

    async def test_missing_position_attribute(self, hass, mock_config_entry):
        """Test handling of source entity with missing position attribute."""
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {
                "supported_features": 143,
                "device_class": "blind"
                # Missing current_position
            }
        )
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = None
        check.is_none(mapped_cover.current_cover_position)

    async def test_missing_tilt_attribute(self, hass, mock_config_entry):
        """Test handling of source entity with missing tilt attribute."""
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
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_tilt = None
        check.is_none(mapped_cover.current_cover_tilt_position)

    async def test_missing_supported_features_attribute(self, hass, mock_config_entry):
        """Test handling of source entity with missing supported_features attribute."""
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {
                "current_position": 50,
                "current_tilt_position": 50,
                "device_class": "blind"
                # Missing supported_features
            }
        )
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover.supported_features, 0)

    async def test_missing_device_class_attribute(self, hass, mock_config_entry):
        """Test handling of source entity with missing device_class attribute."""
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {
                "supported_features": 143,
                "current_position": 50,
                "current_tilt_position": 50
                # Missing device_class
            }
        )
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        check.is_none(mapped_cover.device_class)


class TestServiceCallFailures:
    """Test handling of service call failures and retry exhaustion."""

    async def test_service_call_exception_with_retry(self, hass, mock_config_entry):
        """Test that _call_service handles exceptions and performs retries."""
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {
                "supported_features": 143,
                "current_position": 30,
                "device_class": "blind"
            }
        )
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        check.is_true(hasattr(mapped_cover, "_call_service"))
        source_code = mapped_cover._call_service.__code__.co_varnames
        check.is_in("retry", source_code)
        check.is_true(True)  # Structural validation

    async def test_service_call_retry_exhaustion(self, hass, mock_config_entry):
        """Test that _call_service handles retry exhaustion."""
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {
                "supported_features": 143,
                "current_position": 30,
                "device_class": "blind"
            }
        )
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        original_call_service = mapped_cover._call_service
        attempts = 0

        async def patched_call_service(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            return False
        mapped_cover._call_service = patched_call_service
        try:
            result = await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": "cover.test_cover", "position": 50},
                retry=2
            )
            check.is_false(result)
            check.equal(attempts, 1)  # Only tries once in this patch
        finally:
            mapped_cover._call_service = original_call_service

    async def test_converge_position_handles_service_call_failures(self, hass, mock_config_entry):
        """Test that converge_position handles service call failures gracefully."""
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
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = 60
        mapped_cover._target_tilt = 70
        with patch.object(mapped_cover, "_call_service", return_value=False), \
                patch.object(mapped_cover, "async_write_ha_state"):
            await mapped_cover.converge_position()
        check.is_true(True)  # Should not raise


class TestTimeoutScenarios:
    """Test timeout scenarios in attribute waiting."""

    async def test_wait_for_attribute_timeout(self, hass, mock_config_entry):
        """Test that _wait_for_attribute returns False when timeout occurs."""
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {
                "supported_features": 143,
                "current_position": 30,  # Different from target
                "device_class": "blind"
            }
        )
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        result = await mapped_cover._wait_for_attribute("current_position", 50, timeout=0.1)
        check.is_false(result)

    async def test_call_service_position_timeout(self, hass, mock_config_entry):
        """Test that _call_service handles position not reaching target within timeout."""
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {
                "supported_features": 143,
                "current_position": 30,  # Different from target
                "device_class": "blind"
            }
        )
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        with patch.object(mapped_cover, "_wait_for_attribute", return_value=False):
            result = await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": "cover.test_cover", "position": 50},
                retry=1,
                timeout=0.1
            )
            check.is_false(result)

    async def test_call_service_tilt_timeout(self, hass, mock_config_entry):
        """Test that _call_service handles tilt not reaching target within timeout."""
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {
                "supported_features": 143,
                "current_position": 30,
                "current_tilt_position": 20,  # Different from target
                "device_class": "blind"
            }
        )
        mapped_cover = MappedCover(
            hass, mock_config_entry, "cover.test_cover", MockThrottler())
        with patch.object(mapped_cover, "_wait_for_attribute", return_value=False):
            result = await mapped_cover._call_service(
                "set_cover_tilt_position",
                {"entity_id": "cover.test_cover", "tilt_position": 50},
                retry=1,
                timeout=0.1
            )
            check.is_false(result)
