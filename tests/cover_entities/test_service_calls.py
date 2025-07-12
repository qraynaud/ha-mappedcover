"""Test service call logic for MappedCover._call_service method."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
import logging

from custom_components.mappedcover.cover import MappedCover

# Import fixtures and helpers
from tests.fixtures import *  # Import all shared fixtures
from tests.helpers import create_mock_cover_entity, MockThrottler, create_mock_config_entry

import pytest_check as check


# Remove the patch_async_add_entities fixture entirely.
# In each test, pass an AsyncMock as async_add_entities to the test helper.
# If create_unified_test_environment supports it, do:
# env = await create_unified_test_environment(hass, mock_service_calls=True, return_mocks=True, async_add_entities=AsyncMock())
# Otherwise, patch async_setup_entry or the helper as needed.

from unittest.mock import AsyncMock

# Example for one test:
# async_add_entities = AsyncMock()
# env = await create_unified_test_environment(hass, mock_service_calls=True, return_mocks=True, async_add_entities=async_add_entities)
# mapped_cover = env["entity"]
# ... rest of test ...

# If the helper does not support async_add_entities, you may need to patch async_setup_entry directly in the test.


class TestCallServiceThrottling:
    """Test that _call_service uses the throttler correctly."""

    async def test_throttler_is_used(self, hass, mock_config_entry):
        """Test that _call_service uses the throttler to limit call frequency."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", None)

        # Use a MagicMock throttler with AsyncMock __aenter__ and __aexit__
        throttler_mock = MagicMock()
        throttler_mock.__aenter__ = AsyncMock()
        throttler_mock.__aexit__ = AsyncMock()
        with patch.object(mapped_cover, "_throttler", throttler_mock):
            with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service:
                await mapped_cover._call_service("set_cover_position", {
                    "position": 50,
                    "entity_id": mapped_cover._source_entity_id
                })
                mock_service.assert_called_once_with(
                    "cover", "set_cover_position",
                    {"position": 50, "entity_id": mapped_cover._source_entity_id},
                    blocking=True
                )
                throttler_mock.__aenter__.assert_called_once()
                throttler_mock.__aexit__.assert_called_once()

    async def test_throttler_context_manager(self, hass, mock_config_entry):
        """Test that throttler is used as a context manager correctly."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", None)

        throttler_mock = MagicMock()
        call_order = []

        async def track_enter():
            call_order.append("enter")
            return None

        async def track_exit(*args):
            call_order.append("exit")
            return None
        throttler_mock.__aenter__ = AsyncMock(side_effect=track_enter)
        throttler_mock.__aexit__ = AsyncMock(side_effect=track_exit)
        with patch.object(mapped_cover, "_throttler", throttler_mock):
            with patch("homeassistant.core.ServiceRegistry.async_call", side_effect=lambda *args, **kwargs: call_order.append("service_call")):
                await mapped_cover._call_service("set_cover_position", {
                    "position": 50,
                    "entity_id": mapped_cover._source_entity_id
                })
        check.equal(call_order, ["enter", "service_call", "exit"])


class TestAllowedCommands:
    """Test that _call_service validates the allowed commands."""

    async def test_valid_commands_are_accepted(self, hass, mock_config_entry):
        """Test that valid commands are accepted."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        allowed_commands = [
            "set_cover_position",
            "set_cover_tilt_position",
            "stop_cover",
            "stop_cover_tilt"
        ]
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_async_call:
            for command in allowed_commands:
                result = await mapped_cover._call_service(
                    command,
                    {"entity_id": mapped_cover._source_entity_id}
                )
                check.is_true(result, f"Command {command} should be allowed")

    async def test_invalid_commands_raise_value_error(self, hass, mock_config_entry):
        """Test that invalid commands raise ValueError."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        invalid_commands = [
            "open_cover",
            "close_cover",
            "invalid_command",
            ""
        ]
        for command in invalid_commands:
            with pytest.raises(ValueError, match=f"Command {command} not allowed"):
                await mapped_cover._call_service(
                    command,
                    {"entity_id": mapped_cover._source_entity_id}
                )

    async def test_set_cover_position_updates_timestamp(self, hass, mock_config_entry):
        """Test that set_cover_position command updates _last_position_command timestamp."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        initial_timestamp = mapped_cover._last_position_command
        check.equal(initial_timestamp, 0)
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 70}
            )
            check.is_true(mapped_cover._last_position_command >
                          initial_timestamp)

    async def test_set_cover_tilt_position_does_not_update_timestamp(self, hass, mock_config_entry):
        """Test that set_cover_tilt_position command does NOT update _last_position_command timestamp."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        initial_timestamp = mapped_cover._last_position_command
        check.equal(initial_timestamp, 0)
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            await mapped_cover._call_service(
                "set_cover_tilt_position",
                {"entity_id": mapped_cover._source_entity_id, "tilt_position": 80}
            )
            check.equal(mapped_cover._last_position_command, initial_timestamp)

    async def test_stop_commands_do_not_update_timestamp(self, hass, mock_config_entry):
        """Test that stop commands do NOT update _last_position_command timestamp."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        initial_timestamp = mapped_cover._last_position_command
        check.equal(initial_timestamp, 0)
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            await mapped_cover._call_service(
                "stop_cover",
                {"entity_id": mapped_cover._source_entity_id}
            )
            check.equal(mapped_cover._last_position_command, initial_timestamp)
            await mapped_cover._call_service(
                "stop_cover_tilt",
                {"entity_id": mapped_cover._source_entity_id}
            )
            check.equal(mapped_cover._last_position_command, initial_timestamp)

    async def test_multiple_position_commands_update_timestamp(self, hass, mock_config_entry):
        """Test that multiple position commands update timestamp progressively."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 30}
            )
            first_timestamp = mapped_cover._last_position_command
            check.is_not_none(first_timestamp)
            await asyncio.sleep(0.01)
            await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 80}
            )
            second_timestamp = mapped_cover._last_position_command
            check.is_not_none(second_timestamp)
            check.is_true(second_timestamp > first_timestamp)


class TestPositionConfirmation:
    """Test position confirmation with _wait_for_attribute when retry>0."""

    async def test_waits_for_position_confirmation_when_retry_specified(self, hass, mock_config_entry):
        """Test that _call_service waits for position confirmation when retry>0."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_wait_for_attribute = AsyncMock(return_value=True)
        with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
                patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            result = await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 70},
                retry=3
            )
            # Expect timeout=30 (not DEFAULT_TIMEOUT)
            mock_wait_for_attribute.assert_called_once_with(
                "current_position", 70, timeout=30
            )
            check.is_true(result)

    async def test_retries_on_position_confirmation_failure(self, hass, mock_config_entry):
        """Test that _call_service retries when position confirmation fails."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_wait_for_attribute = AsyncMock(return_value=False)
        with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
                patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()), \
                patch("asyncio.sleep", AsyncMock()):
            result = await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 70},
                retry=2
            )
            check.equal(mock_wait_for_attribute.call_count, 3)
            check.is_false(result)

    async def test_no_wait_for_position_when_retry_zero(self, hass, mock_config_entry):
        """Test that _call_service doesn't wait for position confirmation when retry=0."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_wait_for_attribute = AsyncMock(return_value=True)
        with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
                patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            result = await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 70},
                retry=0
            )
            mock_wait_for_attribute.assert_not_called()
            check.is_true(result)


class TestTiltConfirmation:
    """Test tilt confirmation with _wait_for_attribute when retry>0."""

    async def test_waits_for_tilt_confirmation_when_retry_specified(self, hass, mock_config_entry):
        """Test that _call_service waits for tilt confirmation when retry>0."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_wait_for_attribute = AsyncMock(return_value=True)
        with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
                patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            result = await mapped_cover._call_service(
                "set_cover_tilt_position",
                {"entity_id": mapped_cover._source_entity_id, "tilt_position": 80},
                retry=3
            )
            # Expect timeout=30 (not DEFAULT_TIMEOUT)
            mock_wait_for_attribute.assert_called_once_with(
                "current_tilt_position", 80, timeout=30
            )
            check.is_true(result)

    async def test_retries_on_tilt_confirmation_failure(self, hass, mock_config_entry):
        """Test that _call_service retries when tilt confirmation fails."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_wait_for_attribute = AsyncMock(return_value=False)
        with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
                patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()), \
                patch("asyncio.sleep", AsyncMock()):
            result = await mapped_cover._call_service(
                "set_cover_tilt_position",
                {"entity_id": mapped_cover._source_entity_id, "tilt_position": 80},
                retry=2
            )
            check.equal(mock_wait_for_attribute.call_count, 3)
            check.is_false(result)

    async def test_no_wait_for_tilt_when_retry_zero(self, hass, mock_config_entry):
        """Test that _call_service doesn't wait for tilt confirmation when retry=0."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_wait_for_attribute = AsyncMock(return_value=True)
        with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
                patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            result = await mapped_cover._call_service(
                "set_cover_tilt_position",
                {"entity_id": mapped_cover._source_entity_id, "tilt_position": 80},
                retry=0
            )
            mock_wait_for_attribute.assert_not_called()
            check.is_true(result)


class TestAbortLogic:
    """Test abort_check functionality in _call_service."""

    async def test_aborts_service_call_when_check_returns_true(self, hass, mock_config_entry):
        """Test that service call is aborted when abort_check returns True."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_async_call = AsyncMock()
        abort_check = MagicMock(return_value=True)
        with patch("homeassistant.core.ServiceRegistry.async_call", mock_async_call):
            result = await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 70},
                abort_check=abort_check
            )
            abort_check.assert_called_once()
            mock_async_call.assert_not_called()
            check.is_false(result)

    async def test_continues_service_call_when_check_returns_false(self, hass, mock_config_entry):
        """Test that service call continues when abort_check returns False."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_async_call = AsyncMock()
        abort_check = MagicMock(return_value=False)
        with patch("homeassistant.core.ServiceRegistry.async_call", mock_async_call):
            result = await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 70},
                abort_check=abort_check
            )
            abort_check.assert_called_once()
            mock_async_call.assert_called_once()
            check.is_true(result)

    async def test_abort_check_called_on_each_retry(self, hass, mock_config_entry):
        """Test that abort_check is called on each retry attempt."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_wait_for_attribute = AsyncMock(return_value=False)
        abort_check = MagicMock(side_effect=[False, True])
        with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
                patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()), \
                patch("asyncio.sleep", AsyncMock()):
            result = await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 70},
                retry=2,
                abort_check=abort_check
            )
            check.equal(abort_check.call_count, 2)
            check.is_false(result)


class TestExceptionHandling:
    """Test exception handling and logging in _call_service."""

    async def test_handles_service_call_exceptions(self, hass, mock_config_entry, caplog):
        """Test that _call_service handles exceptions from service calls."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_async_call = AsyncMock(side_effect=Exception("Test error"))
        with patch("homeassistant.core.ServiceRegistry.async_call", mock_async_call), \
                patch("asyncio.sleep", AsyncMock()), \
                caplog.at_level(logging.WARNING):
            result = await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 70},
                retry=0
            )
            check.is_false(result)
            check.is_in(
                "Exception on set_cover_position: Test error", caplog.text)

    async def test_retries_after_exception(self, hass, mock_config_entry):
        """Test that _call_service retries after an exception."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_async_call = AsyncMock(
            side_effect=[Exception("Test error"), None])
        mock_wait_for_attribute = AsyncMock(return_value=True)
        with patch("homeassistant.core.ServiceRegistry.async_call", mock_async_call), \
                patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
                patch("asyncio.sleep", AsyncMock()):
            result = await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 70},
                retry=2
            )
            check.equal(mock_async_call.call_count, 2)
            check.is_true(result)

    async def test_logs_max_retries_reached(self, hass, mock_config_entry, caplog):
        """Test that _call_service logs when max retries are reached."""
        create_mock_cover_entity(hass, "cover.test_cover", state="open",
                                 supported_features=143, current_position=50, current_tilt_position=40)
        config_entry = await create_mock_config_entry(hass)
        mapped_cover = MappedCover(
            hass, config_entry, "cover.test_cover", MockThrottler())
        mock_wait_for_attribute = AsyncMock(return_value=False)
        with patch.object(mapped_cover, "_wait_for_attribute", mock_wait_for_attribute), \
                patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()), \
                patch("asyncio.sleep", AsyncMock()), \
                caplog.at_level(logging.WARNING):
            await mapped_cover._call_service(
                "set_cover_position",
                {"entity_id": mapped_cover._source_entity_id, "position": 70},
                retry=2
            )
            check.is_in(
                f"Max retries (2) reached for set_cover_position", caplog.text)
