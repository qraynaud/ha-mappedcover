"""Tests for state synchronization and reporting for MappedCover."""
import pytest
import pytest_check as check
import time
from unittest.mock import patch, AsyncMock
from custom_components.mappedcover.cover import MappedCover
from tests.helpers import MockThrottler
from tests.fixtures import *


class TestStateReportingDuringMovement:
    """Test state reporting when cover is moving (target values)."""

    @pytest.mark.asyncio
    async def test_reports_target_position_during_movement(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = 70
        check.equal(mapped_cover.current_cover_position, 75)
        check.equal(mapped_cover._source_current_position, 30)

    @pytest.mark.asyncio
    async def test_reports_target_tilt_during_movement(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_tilt = 60
        check.equal(mapped_cover.current_cover_tilt_position, 62)
        check.equal(mapped_cover._source_current_tilt_position, 25)

    @pytest.mark.asyncio
    async def test_is_moving_true_when_targets_set(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = 70
        mapped_cover._target_tilt = 60
        mapped_cover._last_position_command = time.time()
        check.is_true(mapped_cover.is_moving)

    @pytest.mark.asyncio
    async def test_movement_state_indicators_during_targets(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = 80
        check.is_true(mapped_cover.is_opening)
        check.is_false(mapped_cover.is_closing)
        mapped_cover._target_position = 20
        check.is_true(mapped_cover.is_closing)
        check.is_false(mapped_cover.is_opening)


class TestStateReportingWhenStatic:
    """Test state reporting when cover is static (actual source values)."""

    @pytest.mark.asyncio
    async def test_reports_source_position_when_static(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = None
        check.equal(mapped_cover.current_cover_position, 44)

    @pytest.mark.asyncio
    async def test_reports_source_tilt_when_static(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_tilt = None
        check.equal(mapped_cover.current_cover_tilt_position, 34)

    @pytest.mark.asyncio
    async def test_not_moving_when_static_and_old_command(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = None
        mapped_cover._target_tilt = None
        mapped_cover._last_position_command = time.time() - 10
        check.is_false(mapped_cover.is_moving)

    @pytest.mark.asyncio
    async def test_static_state_transitions(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = 70
        mapped_cover._last_position_command = time.time()
        check.equal(mapped_cover.current_cover_position, 75)
        check.is_true(mapped_cover.is_moving)
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {
                "supported_features": 143,
                "current_position": 70,
                "current_tilt_position": 0,
                "device_class": "blind"
            }
        )
        mapped_cover._target_position = None
        mapped_cover._last_position_command = time.time() - 6
        check.equal(mapped_cover.current_cover_position, 75)
        check.is_false(mapped_cover.is_moving)


class TestAsyncWriteHaState:
    """Test async_write_ha_state calls at appropriate times."""

    @pytest.mark.asyncio
    async def test_state_update_called_during_property_changes(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        with patch.object(mapped_cover, 'async_write_ha_state', new_callable=AsyncMock) as mock_write_state:
            hass.states.async_set(
                "cover.test_cover",
                "closing",
                {
                    "supported_features": 143,
                    "current_position": 40,
                    "current_tilt_position": 30,
                    "device_class": "blind"
                }
            )
            check.equal(mapped_cover.current_cover_position, 38)

    @pytest.mark.asyncio
    async def test_state_reporting_consistency(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = None
        mapped_cover._target_tilt = None
        pos1 = mapped_cover.current_cover_position
        pos2 = mapped_cover.current_cover_position
        tilt1 = mapped_cover.current_cover_tilt_position
        tilt2 = mapped_cover.current_cover_tilt_position
        check.equal(pos1, pos2)
        check.equal(tilt1, tilt2)

    @pytest.mark.asyncio
    async def test_state_change_detection_with_targets(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        initial_pos = mapped_cover.current_cover_position
        initial_tilt = mapped_cover.current_cover_tilt_position
        mapped_cover._target_position = 80
        mapped_cover._target_tilt = 70
        moving_pos = mapped_cover.current_cover_position
        moving_tilt = mapped_cover.current_cover_tilt_position
        check.not_equal(moving_pos, initial_pos)
        check.not_equal(moving_tilt, initial_tilt)
        mapped_cover._target_position = None
        mapped_cover._target_tilt = None
        final_pos = mapped_cover.current_cover_position
        final_tilt = mapped_cover.current_cover_tilt_position
        check.equal(final_pos, initial_pos)
        check.equal(final_tilt, initial_tilt)


class TestLastPositionCommandTracking:
    """Test _last_position_command timestamp tracking for is_moving."""

    @pytest.mark.asyncio
    async def test_last_position_command_updated_on_position_set(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._last_position_command, 0)
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            before_time = time.time()
            await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 70})
            after_time = time.time()
            check.is_true(
                before_time <= mapped_cover._last_position_command <= after_time)

    @pytest.mark.asyncio
    async def test_last_position_command_updated_on_tilt_set(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._last_position_command, 0)
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            await mapped_cover._call_service("set_cover_tilt_position", {"entity_id": "cover.test_cover", "tilt_position": 60})
            check.equal(mapped_cover._last_position_command, 0)

    @pytest.mark.asyncio
    async def test_last_position_command_affects_is_moving(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._last_position_command = 0
        check.is_false(mapped_cover.is_moving)
        mapped_cover._last_position_command = time.time()
        check.is_true(mapped_cover.is_moving)
        mapped_cover._last_position_command = time.time() - 6
        check.is_false(mapped_cover.is_moving)

    @pytest.mark.asyncio
    async def test_is_moving_timeout_boundary(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._last_position_command = time.time() - 4.9
        check.is_true(mapped_cover.is_moving)
        mapped_cover._last_position_command = time.time() - 5.1
        check.is_false(mapped_cover.is_moving)

    @pytest.mark.asyncio
    async def test_open_close_commands_set_targets(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())

        def mock_create_tracked_task(coro):
            coro.close()
        with patch.object(mapped_cover, '_create_tracked_task', side_effect=mock_create_tracked_task) as mock_task:
            await mapped_cover.async_open_cover()
            check.equal(mapped_cover._target_position, mapped_cover._max_pos)
            check.equal(mapped_cover._target_tilt, mapped_cover._max_tilt)
            check.is_true(mock_task.called)
            mapped_cover._target_position = None
            mapped_cover._target_tilt = None
            mock_task.reset_mock()
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
            await mapped_cover.async_close_cover()
            check.equal(mapped_cover._target_position, 0)
            check.equal(mapped_cover._target_tilt, 0)
            check.is_true(mock_task.called)


class TestStateIntegrationScenarios:
    """Test integrated state reporting scenarios."""

    @pytest.mark.asyncio
    async def test_full_movement_cycle_state_reporting(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover.current_cover_position, 0)
        check.equal(mapped_cover.current_cover_tilt_position, 0)
        check.is_false(mapped_cover.is_moving)
        check.is_true(mapped_cover.is_closed)
        mapped_cover._target_position = 90
        mapped_cover._target_tilt = 80
        mapped_cover._last_position_command = time.time()
        check.equal(mapped_cover.current_cover_position, 100)
        check.equal(mapped_cover.current_cover_tilt_position, 84)
        check.is_true(mapped_cover.is_moving)
        check.is_false(mapped_cover.is_closed)
        check.is_true(mapped_cover.is_opening)
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {
                "supported_features": 143,
                "current_position": 90,
                "current_tilt_position": 80,
                "device_class": "blind"
            }
        )
        mapped_cover._target_position = None
        mapped_cover._target_tilt = None
        check.equal(mapped_cover.current_cover_position, 100)
        check.equal(mapped_cover.current_cover_tilt_position, 84)
        check.is_false(mapped_cover.is_closed)
        check.is_false(mapped_cover.is_opening)
        check.is_false(mapped_cover.is_closing)
        mapped_cover._last_position_command = time.time() - 6
        check.is_false(mapped_cover.is_moving)

    @pytest.mark.asyncio
    async def test_partial_movement_state_reporting(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        initial_pos = mapped_cover.current_cover_position
        initial_tilt = mapped_cover.current_cover_tilt_position
        mapped_cover._target_position = 60
        mapped_cover._last_position_command = time.time()
        moving_pos = mapped_cover.current_cover_position
        check.not_equal(moving_pos, initial_pos)
        check.is_true(mapped_cover.is_moving)
        check.is_true(mapped_cover.is_opening)
        check.equal(mapped_cover.current_cover_tilt_position, initial_tilt)

    @pytest.mark.asyncio
    async def test_state_with_unavailable_source(self, hass, mock_config_entry):
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
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        check.is_true(mapped_cover.available)
        check.is_true(mapped_cover.current_cover_position is not None)
        check.is_true(mapped_cover.current_cover_tilt_position is not None)
        hass.states.async_set("cover.test_cover", "unavailable", {})
        check.is_false(mapped_cover.available)
        check.is_none(mapped_cover.current_cover_position)
        check.is_none(mapped_cover.current_cover_tilt_position)
        mapped_cover._target_position = 70
        mapped_cover._target_tilt = 50
        check.equal(mapped_cover.current_cover_position, 75)
        check.equal(mapped_cover.current_cover_tilt_position, 50)
