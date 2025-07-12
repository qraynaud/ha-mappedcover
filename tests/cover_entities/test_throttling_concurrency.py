"""
Tests for throttling and concurrency behavior for MappedCover entities.
"""
import asyncio
import time
import pytest
import pytest_check as check
from unittest.mock import patch, AsyncMock, MagicMock
from custom_components.mappedcover.cover import MappedCover
from tests.helpers import MockThrottler
from tests.helpers import wait_for
from tests.fixtures import *


class TestThrottlerIntegration:
    """Test Throttler integration limits service call frequency."""

    @pytest.mark.asyncio
    async def test_throttler_enforces_minimum_interval(self, hass, mock_config_entry):
        call_times = []

        class TimingThrottler:
            def __init__(self, rate_limit, period):
                self.rate_limit = rate_limit
                self.period = period
                self.last_call = 0

            async def __aenter__(self):
                current_time = time.time()
                call_times.append(current_time)
                if self.last_call > 0:
                    time_since_last = current_time - self.last_call
                    if time_since_last < self.period:
                        sleep_time = self.period - time_since_last
                        await asyncio.sleep(sleep_time)
                        call_times[-1] = time.time()
                self.last_call = call_times[-1]
                return self

            async def __aexit__(self, *args, **kwargs):
                pass
        throttler = TimingThrottler(1, 0.1)
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 50,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", return_value=throttler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", throttler)
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            start_time = time.time()
            await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 60})
            await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 70})
            await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 80})
            total_time = time.time() - start_time
        check.equal(len(call_times), 3)
        if len(call_times) >= 2:
            interval1 = call_times[1] - call_times[0]
            check.is_true(interval1 >= 0.09)
        if len(call_times) >= 3:
            interval2 = call_times[2] - call_times[1]
            check.is_true(interval2 >= 0.09)
        check.is_true(total_time >= 0.18)

    @pytest.mark.asyncio
    async def test_throttler_context_manager_usage(self, hass, mock_config_entry):
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 50,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        mock_throttler = MagicMock()
        mock_throttler.__aenter__ = AsyncMock()
        mock_throttler.__aexit__ = AsyncMock()
        with patch("custom_components.mappedcover.cover.Throttler", return_value=mock_throttler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", mock_throttler)
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 70})
        check.is_true(mock_throttler.__aenter__.called)
        check.is_true(mock_throttler.__aexit__.called)

    @pytest.mark.asyncio
    async def test_multiple_service_calls_each_use_throttler(self, hass, mock_config_entry):
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 50,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        throttler_entries = []
        throttler_exits = []

        class TrackingThrottler:
            async def __aenter__(self):
                throttler_entries.append(time.time())
                return self

            async def __aexit__(self, *args, **kwargs):
                throttler_exits.append(time.time())
        throttler = TrackingThrottler()
        with patch("custom_components.mappedcover.cover.Throttler", return_value=throttler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", throttler)
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 60})
            await mapped_cover._call_service("set_cover_tilt_position", {"entity_id": "cover.test_cover", "tilt_position": 80})
            await mapped_cover._call_service("stop_cover", {"entity_id": "cover.test_cover"})
        check.equal(len(throttler_entries), 3)
        check.equal(len(throttler_exits), 3)
        for i in range(3):
            check.is_true(throttler_exits[i] >= throttler_entries[i])


class TestMultipleConvergenceInterruption:
    """Test multiple converge_position calls: new targets interrupt previous runs."""

    @pytest.mark.asyncio
    async def test_new_target_interrupts_previous_convergence(self, hass, mock_config_entry):
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 30,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        convergence_calls = []
        convergence_aborts = []

        async def track_convergence(*args, **kwargs):
            call_id = len(convergence_calls)
            convergence_calls.append(call_id)
            for i in range(5):
                await asyncio.sleep(0.01)
                if mapped_cover._target_position != [30, 60, 80][call_id] if call_id < 3 else None:
                    convergence_aborts.append(call_id)
                    return
        with patch.object(mapped_cover, 'converge_position', side_effect=track_convergence), \
                patch.object(mapped_cover, 'async_write_ha_state'):
            mapped_cover._target_position = 30
            task1 = mapped_cover._create_tracked_task(
                mapped_cover.converge_position())
            await wait_for(lambda: len(convergence_calls) >= 1, error_message="First convergence call did not start in time.")
            mapped_cover._target_position = 60
            task2 = mapped_cover._create_tracked_task(
                mapped_cover.converge_position())
            await wait_for(lambda: len(convergence_calls) >= 2, error_message="Second convergence call did not start in time.")
            mapped_cover._target_position = 80
            task3 = mapped_cover._create_tracked_task(
                mapped_cover.converge_position())
            await wait_for(lambda: len(convergence_calls) >= 3, error_message="Third convergence call did not start in time.")
            await asyncio.gather(task1, task2, task3, return_exceptions=True)
        check.equal(len(convergence_calls), 3)
        check.is_true(len(convergence_aborts) >= 1)

    @pytest.mark.asyncio
    async def test_command_sets_targets_and_triggers_new_convergence(self, hass, mock_config_entry):
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 30,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        convergence_start_times = []
        convergence_targets = []

        async def track_convergence_start():
            convergence_start_times.append(time.time())
            convergence_targets.append(
                (mapped_cover._target_position, mapped_cover._target_tilt))
            await asyncio.sleep(0.05)
        with patch.object(mapped_cover, 'converge_position', side_effect=track_convergence_start):
            start_time = time.time()
            await mapped_cover.async_set_cover_position(position=75)
            await mapped_cover.async_set_cover_tilt_position(tilt_position=80)
            await mapped_cover.async_open_cover()
            command_time = time.time() - start_time
            check.is_true(command_time < 0.1)
            await asyncio.sleep(0.1)
        check.is_true(len(convergence_start_times) >= 2)
        final_targets = convergence_targets[-1] if convergence_targets else (
            None, None)
        check.equal(final_targets[0], 90)
        check.equal(final_targets[1], 95)

    @pytest.mark.asyncio
    async def test_abort_check_detects_target_changes(self, hass, mock_config_entry):
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
        captured_abort_check = None

        async def capture_abort_check(*args, **kwargs):
            nonlocal captured_abort_check
            if 'abort_check' in kwargs:
                captured_abort_check = kwargs['abort_check']
        with patch.object(mapped_cover, '_call_service', side_effect=capture_abort_check), \
                patch.object(mapped_cover, 'async_write_ha_state'):
            convergence_task = asyncio.create_task(
                mapped_cover.converge_position())
            await asyncio.sleep(0.01)
            if captured_abort_check:
                check.is_false(captured_abort_check())
                mapped_cover._target_position = 50
                check.is_true(captured_abort_check())
                mapped_cover._target_position = 70
                mapped_cover._target_tilt = 60
                check.is_true(captured_abort_check())
            convergence_task.cancel()
            try:
                await convergence_task
            except asyncio.CancelledError:
                pass


class TestTargetChangedEventCoordination:
    """Test target_changed_event coordination between operations."""

    @pytest.mark.asyncio
    async def test_convergence_sets_target_changed_event_immediately(self, hass, mock_config_entry):
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 50,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_changed_event.clear()
        check.is_false(mapped_cover._target_changed_event.is_set())
        mapped_cover._target_position = 50
        mapped_cover._target_tilt = 40
        with patch.object(mapped_cover, '_call_service', AsyncMock()), \
                patch.object(mapped_cover, 'async_write_ha_state'):
            await mapped_cover.converge_position()
            check.is_true(mapped_cover._target_changed_event.is_set())

    @pytest.mark.asyncio
    async def test_multiple_wait_operations_interrupted_by_convergence(self, hass, mock_config_entry):
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 50,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        mapped_cover._target_changed_event.clear()
        wait_task1 = asyncio.create_task(
            mapped_cover._target_changed_event.wait())
        wait_task2 = asyncio.create_task(
            mapped_cover._target_changed_event.wait())
        wait_task3 = asyncio.create_task(
            mapped_cover._target_changed_event.wait())
        await wait_for(lambda: not wait_task1.done() and not wait_task2.done() and not wait_task3.done(), error_message="Wait tasks should not be done before event is set.")
        mapped_cover._target_position = 70
        with patch.object(mapped_cover, '_call_service', AsyncMock()), \
                patch.object(mapped_cover, 'async_write_ha_state'):
            await mapped_cover.converge_position()
            await wait_for(lambda: wait_task1.done() and wait_task2.done() and wait_task3.done(), error_message="Wait tasks did not complete after event was set.")
            check.is_true(await wait_task1)
            check.is_true(await wait_task2)
            check.is_true(await wait_task3)

    @pytest.mark.asyncio
    async def test_event_coordinates_between_wait_for_attribute_calls(self, hass, mock_config_entry):
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 30,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        wait_calls = []

        async def track_wait_calls(attribute, target_value, timeout=30, compare=None):
            call_info = {
                'attribute': attribute,
                'target_value': target_value,
                'timeout': timeout,
                'started': time.time(),
                'event_was_set': mapped_cover._target_changed_event.is_set()
            }
            wait_calls.append(call_info)
            # Eliminate loop and sleep for speed: check event immediately
            if mapped_cover._target_changed_event.is_set():
                call_info['interrupted'] = True
                call_info['completed'] = time.time()
                return False
            call_info['interrupted'] = False
            call_info['completed'] = time.time()
            return True
        with patch.object(mapped_cover, '_wait_for_attribute', side_effect=track_wait_calls):
            mapped_cover._target_position = 70
            mapped_cover._target_tilt = 80
            convergence_task = asyncio.create_task(
                mapped_cover.converge_position())
            await wait_for(lambda: len(wait_calls) >= 1, error_message="No wait_for_attribute calls started in time.")
            mapped_cover._target_position = 50
            mapped_cover._target_tilt = 60
            new_convergence_task = asyncio.create_task(
                mapped_cover.converge_position())
            await asyncio.gather(convergence_task, new_convergence_task, return_exceptions=True)
        check.is_true(len(wait_calls) >= 1)
        interrupted_calls = [
            call for call in wait_calls if call.get('interrupted', False)]
        check.is_true(len(interrupted_calls) >= 1)


class TestAsyncTaskCreation:
    """Test async task creation for converge_position doesn't block commands."""

    @pytest.mark.asyncio
    async def test_commands_complete_immediately_despite_convergence(self, hass, mock_config_entry):
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 30,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())

        async def slow_convergence():
            await asyncio.sleep(0.2)
        with patch.object(mapped_cover, 'converge_position', side_effect=slow_convergence):
            start_time = time.time()
            await mapped_cover.async_set_cover_position(position=75)
            command1_time = time.time() - start_time
            await mapped_cover.async_set_cover_tilt_position(tilt_position=80)
            command2_time = time.time() - start_time
            await mapped_cover.async_open_cover()
            command3_time = time.time() - start_time
            check.is_true(command1_time < 0.05)
            check.is_true(command2_time < 0.1)
            check.is_true(command3_time < 0.15)
            await asyncio.sleep(0.3)

    @pytest.mark.asyncio
    async def test_convergence_tasks_are_properly_tracked(self, hass, mock_config_entry):
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 30,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        initial_task_count = len(mapped_cover._running_tasks)
        convergence_started = []
        convergence_finished = []

        async def track_convergence():
            convergence_started.append(time.time())
            await asyncio.sleep(0.05)
            convergence_finished.append(time.time())
        with patch.object(mapped_cover, 'converge_position', side_effect=track_convergence):
            await mapped_cover.async_set_cover_position(position=75)
            await mapped_cover.async_set_cover_tilt_position(tilt_position=80)
            mid_task_count = len(mapped_cover._running_tasks)
            check.is_true(mid_task_count >= initial_task_count)
            await asyncio.sleep(0.1)
            final_task_count = len(mapped_cover._running_tasks)
        check.is_true(len(convergence_started) >= 2)
        check.equal(len(convergence_finished), len(convergence_started))
        check.is_true(final_task_count <= initial_task_count + 1)

    @pytest.mark.asyncio
    async def test_task_cleanup_on_entity_removal(self, hass, mock_config_entry):
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 30,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        self_mapped_covers = getattr(self, 'mapped_covers', [])
        self_mapped_covers.append(mapped_cover)
        task_cancelled = []

        async def long_convergence():
            try:
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                task_cancelled.append(True)
                raise
        with patch.object(mapped_cover, 'converge_position', side_effect=long_convergence):
            await mapped_cover.async_set_cover_position(position=75)
            await mapped_cover.async_set_cover_tilt_position(tilt_position=80)
            check.is_true(len(mapped_cover._running_tasks) >= 1)
            await mapped_cover.async_will_remove_from_hass()
            await asyncio.sleep(0.01)
            check.equal(len(mapped_cover._running_tasks), 0)
            check.is_true(len(task_cancelled) >= 1)

    @pytest.mark.asyncio
    async def test_concurrent_convergence_tasks_do_not_interfere(self, hass, mock_config_entry):
        hass.states.async_set(
            "cover.test_cover",
            "open",
            {"supported_features": 143, "current_position": 30,
                "current_tilt_position": 40, "device_class": "blind"}
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, mock_config_entry, "cover.test_cover", MockThrottler())
        convergence_operations = []

        async def track_convergence_operation():
            operation_id = len(convergence_operations)
            operation_info = {
                'id': operation_id,
                'started': time.time(),
                'targets_at_start': (mapped_cover._target_position, mapped_cover._target_tilt),
                'aborted': False
            }
            convergence_operations.append(operation_info)
            for i in range(10):
                await asyncio.sleep(0.001)
                current_targets = (
                    mapped_cover._target_position, mapped_cover._target_tilt)
                if current_targets != operation_info['targets_at_start']:
                    operation_info['aborted'] = True
                    operation_info['finished'] = time.time()
                    return
            operation_info['finished'] = time.time()
        with patch.object(mapped_cover, 'converge_position', side_effect=track_convergence_operation):
            await mapped_cover.async_set_cover_position(position=60)
            await wait_for(lambda: len(convergence_operations) >= 1, error_message="First convergence operation did not start in time.")
            await mapped_cover.async_set_cover_position(position=70)
            await wait_for(lambda: len(convergence_operations) >= 2, error_message="Second convergence operation did not start in time.")
            await mapped_cover.async_set_cover_tilt_position(tilt_position=80)
            await wait_for(lambda: len(convergence_operations) >= 3, error_message="Third convergence operation did not start in time.")
            await mapped_cover.async_open_cover()
            await wait_for(
                lambda: len(convergence_operations) >= 3 and all(
                    'finished' in op for op in convergence_operations),
                timeout=0.2,
                error_message="Not all convergence operations finished in time."
            )
        aborted_operations = [
            op for op in convergence_operations if op.get('aborted', False)]
        check.is_true(len(aborted_operations) >= 1)
        if convergence_operations:
            last_operation = convergence_operations[-1]
            check.is_false(last_operation.get('aborted', True))
            check.is_true('finished' in last_operation)
