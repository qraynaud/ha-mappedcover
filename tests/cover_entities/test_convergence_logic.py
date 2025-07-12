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
from unittest.mock import patch
import pytest_check as check

from custom_components.mappedcover.cover import MappedCover
# Import from helpers
from tests.helpers import (
    MockThrottler,
    assert_service_called,
    assert_service_not_called,
    run_unified_convergence_test,
    run_abort_logic_test,
    run_target_cleanup_test,
)
# Import fixtures
from tests.fixtures import *

# =============================================================================
# TILT-FIRST LOGIC TESTS
# =============================================================================


class TestTiltFirstLogic:
    """Test tilt-first positioning logic in convergence."""

    async def test_sets_tilt_first_when_both_targets_and_position_needs_move_not_moving(self, hass, mock_config_entry):
        """Test tilt is set first when both position+tilt set, position≠current, not recently moving."""
        call_tracker, _, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            target_position=70,
            target_tilt=80,
            current_position=30,
            current_tilt_position=40,
            is_moving=False
        )
        # Should call tilt first, then position, then tilt again (final target)
        expected_calls = [
            "set_cover_tilt_position",
            "set_cover_position",
            "set_cover_tilt_position"
        ]
        actual_calls = [c if isinstance(c, str) else c[0]
                        for c in call_tracker]
        check.equal(actual_calls, expected_calls,
                    f"Expected call order {expected_calls}, got {actual_calls}")

    async def test_does_not_set_tilt_first_when_recently_moving(self, hass, mock_config_entry):
        """Test tilt is NOT set first when cover is recently moving."""
        call_tracker, _, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            target_position=70,
            target_tilt=80,
            current_position=30,
            current_tilt_position=40,
            is_moving=True  # Recently moving
        )

        # Should set position first, then tilt
        check.equal(len(call_tracker), 2)
        check.equal(call_tracker[0], "set_cover_position")
        check.equal(call_tracker[1], "set_cover_tilt_position")

    async def test_does_not_set_tilt_first_when_position_equals_current(self, hass, mock_config_entry):
        """Test tilt is NOT set first when target position equals current position."""
        call_tracker, _, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            target_position=70,
            target_tilt=80,
            current_position=70,  # Same as target
            current_tilt_position=40,
            is_moving=False
        )

        # Should only set tilt, not tilt-first logic
        check.equal(len(call_tracker), 1)
        check.equal(call_tracker[0], "set_cover_tilt_position")

    async def test_does_not_set_tilt_first_when_only_one_target(self, hass, mock_config_entry):
        """Test tilt-first logic only applies when both position and tilt targets are set."""
        call_tracker, _, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            target_position=70,
            target_tilt=None,  # No tilt target
            current_position=30,
            current_tilt_position=40,
            is_moving=False
        )

        # Should only call position service
        check.equal(len(call_tracker), 1)
        check.equal(call_tracker[0], "set_cover_position")

# =============================================================================
# STOP-IF-MOVING TESTS
# =============================================================================


class TestStopIfMovingLogic:
    """Test stop-if-moving behavior in convergence."""

    async def test_stops_cover_when_moving_and_at_target_position(self, hass, mock_config_entry):
        call_tracker, _, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            target_position=70,
            current_position=70,  # At target!
            is_moving=True,
            stop_if_moving=True,
            mock_wait_for_attribute=True
        )
        assert_service_called(call_tracker, "stop_cover")
        assert_service_not_called(call_tracker, "set_cover_position")

    async def test_does_not_stop_when_not_moving(self, hass, mock_config_entry):
        """Test that cover is not stopped when not moving."""
        call_tracker, _, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            target_position=70,
            current_position=30,
            is_moving=False,
            stop_if_moving=True,
            mock_wait_for_attribute=True
        )

        # Should only set position, no stop
        check.equal(len(call_tracker), 1)
        check.equal(call_tracker[0], "set_cover_position")

    async def test_does_not_stop_when_moving_but_not_at_target(self, hass, mock_config_entry):
        """Test that cover is not stopped when moving but not at the target position."""
        call_tracker, _, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            target_position=70,
            current_position=50,  # Different from target
            is_moving=True,
            stop_if_moving=True,
            mock_wait_for_attribute=True
        )
        assert_service_called(call_tracker, "set_cover_position")
        assert_service_not_called(call_tracker, "stop_cover")

# =============================================================================
# CLOSE-TILT-IF-DOWN TESTS
# =============================================================================


class TestCloseTiltIfDownBehavior:
    """Test close-tilt-if-down behavior."""

    async def test_sets_tilt_zero_before_target_when_close_tilt_if_down_and_decreasing(
        self, hass, mock_config_entry
    ):
        """Test that tilt is set to 0 before position when decreasing and close_tilt_if_down is enabled."""
        call_tracker, _, _ = await run_unified_convergence_test(
            hass,
            mock_config_entry,
            current_position=100,
            current_tilt_position=50,
            target_position=0,
            target_tilt=30,
            expect_position_call=True,
            expect_tilt_call=True,
            close_tilt_if_down=True
        )
        assert_service_called(
            call_tracker, "set_cover_tilt_position", tilt_position=0)
        assert_service_called(call_tracker, "set_cover_position", position=0)

    async def test_does_not_set_tilt_zero_when_close_tilt_if_down_disabled(
        self, hass, mock_config_entry
    ):
        """Test that tilt is not set to 0 when close_tilt_if_down is disabled."""
        call_tracker, _, _ = await run_unified_convergence_test(
            hass,
            mock_config_entry,
            current_position=100,
            current_tilt_position=50,
            target_position=0,
            target_tilt=30,
            expect_position_call=True,
            expect_tilt_call=True,
            close_tilt_if_down=False
        )
        assert_service_called(
            call_tracker, "set_cover_tilt_position", tilt_position=30)
        assert_service_called(call_tracker, "set_cover_position", position=0)

    async def test_does_not_set_tilt_zero_when_tilt_increasing(self, hass, mock_config_entry):
        """Test that tilt is not set to 0 when the tilt target is increasing."""
        call_tracker, _, _ = await run_unified_convergence_test(
            hass,
            mock_config_entry,
            current_position=100,
            current_tilt_position=50,
            target_position=0,
            target_tilt=70,
            expect_position_call=True,
            expect_tilt_call=True,
            close_tilt_if_down=True
        )
        assert_service_called(
            call_tracker, "set_cover_tilt_position", tilt_position=30)
        assert_service_called(call_tracker, "set_cover_position", position=0)

    async def test_does_not_set_tilt_zero_when_position_target_exists(
        self, hass, mock_config_entry
    ):
        """Test that tilt is not set to 0 when position target exists."""
        call_tracker, _, _ = await run_unified_convergence_test(
            hass,
            mock_config_entry,
            current_position=100,
            current_tilt_position=50,
            target_position=None,
            target_tilt=30,
            expect_position_call=False,
            expect_tilt_call=True,
            close_tilt_if_down=True
        )
        assert_service_called(
            call_tracker, "set_cover_tilt_position", tilt_position=30)
        assert_service_not_called(call_tracker, "set_cover_position")

# Additional tests will be migrated as we continue...

# =============================================================================
# EVENT, POSITION/TILT CONVERGENCE, ABORT, AND CLEANUP TESTS (MIGRATED)
# =============================================================================


class TestTargetChangedEvent:
    async def test_event_is_set_immediately_on_convergence_start(self, hass, mock_config_entry):
        from unittest.mock import AsyncMock
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 50,
             "current_tilt_position": 30, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_changed_event.clear()
        check.is_false(mapped_cover._target_changed_event.is_set())
        mapped_cover._target_position = 50
        mapped_cover._target_tilt = 30
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
            check.is_true(event_was_set)

    async def test_event_interrupts_waiting_operations(self, hass, mock_config_entry):
        from unittest.mock import AsyncMock
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 50,
             "current_tilt_position": 30, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_changed_event.clear()
        wait_task = asyncio.create_task(
            mapped_cover._target_changed_event.wait())
        check.is_false(wait_task.done())
        mapped_cover._target_position = 70
        try:
            with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock), \
                    patch.object(mapped_cover, 'async_write_ha_state'):
                await mapped_cover.converge_position()
            await asyncio.sleep(0.01)
            check.is_true(wait_task.done())
        finally:
            if not wait_task.done():
                wait_task.cancel()
                try:
                    await wait_task
                except asyncio.CancelledError:
                    pass


class TestPositionConvergence:
    async def test_sets_position_when_current_differs_from_target(self, hass, mock_config_entry):
        from unittest.mock import ANY
        from tests.helpers import run_unified_convergence_test
        call_tracker, mock_call_service, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            current_position=30,
            target_position=70,
            expect_position_call=True
        )
        mock_call_service.assert_called_with(
            "set_cover_position",
            {"entity_id": "cover.test_cover", "position": 70},
            retry=3,
            abort_check=ANY
        )

    async def test_skips_position_when_current_equals_target(self, hass, mock_config_entry):
        from tests.helpers import run_unified_convergence_test
        call_tracker, _mock_call_service, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            current_position=70,
            target_position=70,
            expect_position_call=False
        )
        assert_service_not_called(call_tracker, "set_cover_position")

    async def test_skips_position_when_target_is_none(self, hass, mock_config_entry):
        from tests.helpers import run_unified_convergence_test
        call_tracker, _mock_call_service, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            current_position=50,
            target_position=None,
            target_tilt=80,
            expect_position_call=False
        )
        assert_service_not_called(call_tracker, "set_cover_position")
        assert_service_called(call_tracker, "set_cover_tilt_position")


class TestTiltConvergence:
    async def test_sets_tilt_when_target_is_set(self, hass, mock_config_entry):
        from unittest.mock import ANY
        from tests.helpers import run_unified_convergence_test
        call_tracker, mock_call_service, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            current_tilt_position=30,
            target_tilt=80,
            expect_tilt_call=True
        )
        mock_call_service.assert_called_with(
            "set_cover_tilt_position",
            {"entity_id": "cover.test_cover", "tilt_position": 80},
            retry=3,
            abort_check=ANY
        )

    async def test_skips_tilt_when_target_is_none(self, hass, mock_config_entry):
        from tests.helpers import run_unified_convergence_test
        call_tracker, _mock_call_service, _ = await run_unified_convergence_test(
            hass, mock_config_entry,
            current_tilt_position=30,
            target_tilt=None,
            target_position=70,
            expect_tilt_call=False
        )
        assert_service_not_called(call_tracker, "set_cover_tilt_position")
        assert_service_called(call_tracker, "set_cover_position")

    async def test_waits_for_tilt_when_position_was_set_but_not_reached(self, hass, mock_config_entry):
        from unittest.mock import AsyncMock, PropertyMock
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 30,
             "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = 70
        mapped_cover._target_tilt = 80
        with patch.object(mapped_cover, '_call_service', new_callable=AsyncMock), \
                patch.object(mapped_cover, 'async_write_ha_state'), \
                patch.object(mapped_cover, '_wait_for_attribute', new_callable=AsyncMock, return_value=False) as mock_wait, \
                patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):
            await mapped_cover.converge_position()
            mock_wait.assert_called_with("current_tilt_position", 80, 5)

    async def test_skips_wait_when_tilt_reached_during_position_move(self, hass, mock_config_entry):
        from unittest.mock import AsyncMock, PropertyMock
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 30,
             "current_tilt_position": 80, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = 70
        mapped_cover._target_tilt = 80
        service_calls = []

        async def track_calls(service_name, params, **kwargs):
            service_calls.append((service_name, params))
            if service_name == "set_cover_position":
                hass.states.async_set(
                    "cover.test_cover",
                    "open",
                    {"current_position": 70, "current_tilt_position": 80}
                )
        with patch.object(mapped_cover, '_call_service', side_effect=track_calls), \
                patch.object(mapped_cover, 'async_write_ha_state'), \
                patch.object(mapped_cover, '_wait_for_attribute', new_callable=AsyncMock, return_value=True), \
                patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):
            await mapped_cover.converge_position()
            tilt_calls = [
                (svc, params) for svc, params in service_calls if svc == "set_cover_tilt_position"]
            for _, params in tilt_calls:
                check.equal(params["tilt_position"], 80)
            position_calls = [
                (svc, params) for svc, params in service_calls if svc == "set_cover_position"]
            check.equal(len(position_calls), 1)
            check.equal(position_calls[0][1]["position"], 70)


class TestAbortLogic:
    async def test_aborts_early_when_target_position_changes(self, hass, mock_config_entry):
        call_count, mapped_cover = await run_abort_logic_test(
            hass, mock_config_entry,
            change_position_target=True,
            change_tilt_target=False
        )
        check.equal(call_count, 1)
        check.equal(mapped_cover._target_position, 50)
        check.equal(mapped_cover._target_tilt, 80)

    async def test_aborts_early_when_target_tilt_changes(self, hass, mock_config_entry):
        call_count, mapped_cover = await run_abort_logic_test(
            hass, mock_config_entry,
            change_position_target=False,
            change_tilt_target=True
        )
        check.equal(call_count, 1)
        check.equal(mapped_cover._target_position, 70)
        check.equal(mapped_cover._target_tilt, 90)

    async def test_aborts_during_close_tilt_if_down_phase(self, hass, mock_config_entry):
        hass.config_entries.async_update_entry(
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
            {"supported_features": 143, "current_position": 50,
             "current_tilt_position": 80, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = None
        mapped_cover._target_tilt = 40
        call_count = 0

        async def change_target_during_zero_tilt(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mapped_cover._target_tilt = 90
        with patch.object(mapped_cover, '_call_service', side_effect=change_target_during_zero_tilt), \
                patch.object(mapped_cover, 'async_write_ha_state'):
            await mapped_cover.converge_position()
            check.equal(call_count, 1)
            check.equal(mapped_cover._target_tilt, 90)

    async def test_continues_when_targets_unchanged(self, hass, mock_config_entry):
        from unittest.mock import PropertyMock
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 30,
             "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_position = 70
        mapped_cover._target_tilt = 80
        call_order = []

        async def track_calls(service_name, *args, **kwargs):
            call_order.append(service_name)
            if service_name == "set_cover_position":
                hass.states.async_set(
                    "cover.test_cover",
                    "open",
                    {"current_position": 70, "current_tilt_position": 40}
                )

        async def mock_wait(*args, **kwargs):
            return True
        with patch.object(mapped_cover, '_call_service', side_effect=track_calls), \
                patch.object(mapped_cover, 'async_write_ha_state'), \
                patch.object(mapped_cover, '_wait_for_attribute', side_effect=mock_wait), \
                patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):
            await mapped_cover.converge_position()
            check.equal(len(call_order), 2)
            check.equal(sorted(call_order), sorted(
                ["set_cover_position", "set_cover_tilt_position"]))


class TestTargetCleanup:
    async def test_clears_targets_when_convergence_completes_successfully(self, hass, mock_config_entry):
        mapped_cover, mock_write_state = await run_target_cleanup_test(
            hass, mock_config_entry,
            set_position_target=True,
            set_tilt_target=True
        )
        check.is_none(mapped_cover._target_position)
        check.is_none(mapped_cover._target_tilt)
        mock_write_state.assert_called()

    async def test_clears_only_position_target_when_only_position_set(self, hass, mock_config_entry):
        mapped_cover, _ = await run_target_cleanup_test(
            hass, mock_config_entry,
            set_position_target=True,
            set_tilt_target=False
        )
        check.is_none(mapped_cover._target_position)
        check.is_none(mapped_cover._target_tilt)

    async def test_clears_only_tilt_target_when_only_tilt_set(self, hass, mock_config_entry):
        mapped_cover, _ = await run_target_cleanup_test(
            hass, mock_config_entry,
            set_position_target=False,
            set_tilt_target=True
        )
        check.is_none(mapped_cover._target_position)
        check.is_none(mapped_cover._target_tilt)

    async def test_does_not_clear_targets_when_aborted(self, hass, mock_config_entry):
        mapped_cover, _ = await run_target_cleanup_test(
            hass, mock_config_entry,
            set_position_target=True,
            set_tilt_target=True,
            abort_during_execution=True
        )
        check.equal(mapped_cover._target_position, 50)
        check.equal(mapped_cover._target_tilt, 80)
