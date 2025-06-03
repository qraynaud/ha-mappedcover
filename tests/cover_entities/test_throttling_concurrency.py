"""
Test throttling and concurrency behavior for MappedCover entities.

Tests the throttling integration and concurrency management including:
- Throttler integration limiting service call frequency  
- Multiple converge_position calls with target interruption
- target_changed_event coordination between operations
- Async task creation for converge_position doesn't block commands
"""
import asyncio
import time
from unittest.mock import patch, AsyncMock, MagicMock, call

from custom_components.mappedcover.cover import MappedCover
from tests.helpers import MockThrottler
from tests.fixtures import *  # Import all shared fixtures


class TestThrottlerIntegration:
    """Test Throttler integration limits service call frequency."""

    async def test_throttler_enforces_minimum_interval(self, hass, mock_config_entry):
        """Test that throttler enforces minimum interval between service calls."""
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

        # Create a real throttler that enforces timing
        call_times = []

        class TimingThrottler:
            """Throttler that records call timing."""
            def __init__(self, rate_limit, period):
                self.rate_limit = rate_limit
                self.period = period
                self.last_call = 0
                
            async def __aenter__(self):
                current_time = time.time()
                call_times.append(current_time)
                
                # Enforce minimum interval
                if self.last_call > 0:
                    time_since_last = current_time - self.last_call
                    if time_since_last < self.period:
                        sleep_time = self.period - time_since_last
                        await asyncio.sleep(sleep_time)
                        call_times[-1] = time.time()  # Update actual call time
                
                self.last_call = call_times[-1]
                return self
                
            async def __aexit__(self, *args, **kwargs):
                pass

        # Use throttler with 100ms minimum interval
        throttler = TimingThrottler(1, 0.1)  # 1 call per 100ms

        with patch("custom_components.mappedcover.cover.Throttler", return_value=throttler):
            mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", throttler)

        # Mock the service call to avoid actual execution
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()) as mock_service:
            # Make multiple rapid service calls
            start_time = time.time()
            
            await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 60})
            await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 70})
            await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 80})
            
            total_time = time.time() - start_time

            # Should have enforced minimum intervals
            assert len(call_times) == 3
            
            # Check that intervals were enforced (allowing some tolerance for test execution time)
            if len(call_times) >= 2:
                interval1 = call_times[1] - call_times[0]
                assert interval1 >= 0.09, f"First interval too short: {interval1}"
                
            if len(call_times) >= 3:
                interval2 = call_times[2] - call_times[1]  
                assert interval2 >= 0.09, f"Second interval too short: {interval2}"

            # Total time should be at least 200ms for 3 calls with 100ms intervals
            assert total_time >= 0.18, f"Total time too short: {total_time}"

    async def test_throttler_context_manager_usage(self, hass, mock_config_entry):
        """Test that _call_service correctly uses throttler as context manager."""
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

        # Create a mock throttler to track context manager usage
        mock_throttler = MagicMock()
        mock_throttler.__aenter__ = AsyncMock()
        mock_throttler.__aexit__ = AsyncMock()

        with patch("custom_components.mappedcover.cover.Throttler", return_value=mock_throttler):
            mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", mock_throttler)

        # Mock the service call to avoid actual execution
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 70})

        # Verify throttler context manager was used
        mock_throttler.__aenter__.assert_called_once()
        mock_throttler.__aexit__.assert_called_once()

    async def test_multiple_service_calls_each_use_throttler(self, hass, mock_config_entry):
        """Test that each service call independently uses the throttler."""
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

        # Track throttler usage
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
            mapped_cover = MappedCover(hass, mock_config_entry, "cover.test_cover", throttler)

        # Mock the service call to avoid actual execution
        with patch("homeassistant.core.ServiceRegistry.async_call", AsyncMock()):
            # Make multiple service calls
            await mapped_cover._call_service("set_cover_position", {"entity_id": "cover.test_cover", "position": 60})
            await mapped_cover._call_service("set_cover_tilt_position", {"entity_id": "cover.test_cover", "tilt_position": 80})
            await mapped_cover._call_service("stop_cover", {"entity_id": "cover.test_cover"})

        # Each call should have used the throttler
        assert len(throttler_entries) == 3
        assert len(throttler_exits) == 3

        # Entries and exits should be properly paired
        for i in range(3):
            assert throttler_exits[i] >= throttler_entries[i]


class TestMultipleConvergenceInterruption:
    """Test multiple converge_position calls: new targets interrupt previous runs."""

    async def test_new_target_interrupts_previous_convergence(self, hass, mock_config_entry):
        """Test that setting new targets interrupts ongoing convergence operations."""
        # Set up test cover
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

        convergence_calls = []
        convergence_aborts = []

        async def track_convergence(*args, **kwargs):
            """Track convergence calls and check for aborts."""
            call_id = len(convergence_calls)
            convergence_calls.append(call_id)
            
            # Simulate some work and check for abort
            for i in range(5):
                await asyncio.sleep(0.01)
                # Check if targets changed (abort condition)
                if mapped_cover._target_position != [30, 60, 80][call_id] if call_id < 3 else None:
                    convergence_aborts.append(call_id)
                    return  # Abort this convergence

        with patch.object(mapped_cover, 'converge_position', side_effect=track_convergence), \
             patch.object(mapped_cover, 'async_write_ha_state'):

            # First convergence call
            mapped_cover._target_position = 30
            task1 = mapped_cover._create_tracked_task(mapped_cover.converge_position())
            await asyncio.sleep(0.02)  # Let it start

            # Second call interrupts first
            mapped_cover._target_position = 60
            task2 = mapped_cover._create_tracked_task(mapped_cover.converge_position())
            await asyncio.sleep(0.02)

            # Third call interrupts second
            mapped_cover._target_position = 80
            task3 = mapped_cover._create_tracked_task(mapped_cover.converge_position())

            # Wait for all tasks to complete
            await asyncio.gather(task1, task2, task3, return_exceptions=True)

        # All convergence calls should have been made
        assert len(convergence_calls) == 3

        # Earlier calls should have been aborted by target changes
        # (The exact abort behavior depends on timing, but at least some should abort)
        assert len(convergence_aborts) >= 1

    async def test_command_sets_targets_and_triggers_new_convergence(self, hass, mock_config_entry):
        """Test that new commands set targets and trigger convergence without blocking."""
        # Set up test cover
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

        convergence_start_times = []
        convergence_targets = []

        async def track_convergence_start():
            """Track when convergence starts and what targets it sees."""
            convergence_start_times.append(time.time())
            convergence_targets.append((mapped_cover._target_position, mapped_cover._target_tilt))
            await asyncio.sleep(0.05)  # Simulate convergence work

        with patch.object(mapped_cover, 'converge_position', side_effect=track_convergence_start):
            start_time = time.time()

            # Issue rapid commands - they should not block
            await mapped_cover.async_set_cover_position(position=75)  # 70 in source scale
            await mapped_cover.async_set_cover_tilt_position(tilt_position=80)  # ~77 in source scale
            await mapped_cover.async_open_cover()  # max positions

            command_time = time.time() - start_time

            # Commands should complete quickly (not blocked by convergence)
            assert command_time < 0.1, f"Commands took too long: {command_time}"

            # Wait a bit for convergence tasks to start
            await asyncio.sleep(0.1)

        # Multiple convergence operations should have been triggered
        assert len(convergence_start_times) >= 2

        # Targets should reflect the commands
        final_targets = convergence_targets[-1] if convergence_targets else (None, None)
        assert final_targets[0] == 90  # open_cover sets max position
        assert final_targets[1] == 95  # open_cover sets max tilt

    async def test_abort_check_detects_target_changes(self, hass, mock_config_entry):
        """Test that abort_check function correctly detects target changes during convergence."""
        # Set up test cover
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

        # Set initial targets
        mapped_cover._target_position = 70
        mapped_cover._target_tilt = 80

        # Start convergence and capture the abort_check function
        captured_abort_check = None

        async def capture_abort_check(*args, **kwargs):
            """Capture the abort_check function from _call_service calls."""
            nonlocal captured_abort_check
            if 'abort_check' in kwargs:
                captured_abort_check = kwargs['abort_check']

        with patch.object(mapped_cover, '_call_service', side_effect=capture_abort_check), \
             patch.object(mapped_cover, 'async_write_ha_state'):

            # Trigger convergence
            convergence_task = asyncio.create_task(mapped_cover.converge_position())
            await asyncio.sleep(0.01)  # Let convergence start

            # Initially, abort_check should return False
            if captured_abort_check:
                assert not captured_abort_check(), "Should not abort with unchanged targets"

                # Change targets - abort_check should now return True
                mapped_cover._target_position = 50
                assert captured_abort_check(), "Should abort when position target changes"

                # Restore position but change tilt
                mapped_cover._target_position = 70
                mapped_cover._target_tilt = 60
                assert captured_abort_check(), "Should abort when tilt target changes"

            # Clean up
            convergence_task.cancel()
            try:
                await convergence_task
            except asyncio.CancelledError:
                pass


class TestTargetChangedEventCoordination:
    """Test target_changed_event coordination between operations."""

    async def test_convergence_sets_target_changed_event_immediately(self, hass, mock_config_entry):
        """Test that converge_position sets target_changed_event immediately when starting."""
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

        # Clear the event initially
        mapped_cover._target_changed_event.clear()
        assert not mapped_cover._target_changed_event.is_set()

        # Set targets but ensure convergence is minimal
        mapped_cover._target_position = 50  # Same as current - no service calls needed
        mapped_cover._target_tilt = 40     # Same as current - no service calls needed

        with patch.object(mapped_cover, '_call_service', AsyncMock()), \
             patch.object(mapped_cover, 'async_write_ha_state'):

            # Start convergence
            await mapped_cover.converge_position()

            # Event should be set immediately
            assert mapped_cover._target_changed_event.is_set()

    async def test_multiple_wait_operations_interrupted_by_convergence(self, hass, mock_config_entry):
        """Test that multiple operations waiting on target_changed_event are interrupted by convergence."""
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

        # Clear the event
        mapped_cover._target_changed_event.clear()

        # Create multiple tasks waiting for the event
        wait_task1 = asyncio.create_task(mapped_cover._target_changed_event.wait())
        wait_task2 = asyncio.create_task(mapped_cover._target_changed_event.wait())
        wait_task3 = asyncio.create_task(mapped_cover._target_changed_event.wait())

        # Initially, tasks should not be done
        await asyncio.sleep(0.01)
        assert not wait_task1.done()
        assert not wait_task2.done()
        assert not wait_task3.done()

        # Set targets and trigger convergence
        mapped_cover._target_position = 70

        with patch.object(mapped_cover, '_call_service', AsyncMock()), \
             patch.object(mapped_cover, 'async_write_ha_state'):

            # Trigger convergence - should set the event
            await mapped_cover.converge_position()

            # Brief wait for event propagation
            await asyncio.sleep(0.01)

            # All waiting tasks should now be complete
            assert wait_task1.done()
            assert wait_task2.done()
            assert wait_task3.done()

            # All should have returned True (event was set)
            assert await wait_task1 is True
            assert await wait_task2 is True
            assert await wait_task3 is True

    async def test_event_coordinates_between_wait_for_attribute_calls(self, hass, mock_config_entry):
        """Test that target_changed_event properly coordinates between _wait_for_attribute calls."""
        # Set up test cover
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

        wait_calls = []

        async def track_wait_calls(attribute, target_value, timeout=30, compare=None):
            """Track _wait_for_attribute calls and simulate waiting."""
            call_info = {
                'attribute': attribute,
                'target_value': target_value,
                'timeout': timeout,
                'started': time.time(),
                'event_was_set': mapped_cover._target_changed_event.is_set()
            }
            wait_calls.append(call_info)

            # Simulate waiting with event checking
            for i in range(10):  # Check 10 times over 100ms
                await asyncio.sleep(0.01)
                if mapped_cover._target_changed_event.is_set():
                    call_info['interrupted'] = True
                    call_info['completed'] = time.time()
                    return False  # Interrupted
                    
            call_info['interrupted'] = False
            call_info['completed'] = time.time()
            return True  # Completed normally

        with patch.object(mapped_cover, '_wait_for_attribute', side_effect=track_wait_calls):
            # Start a long-running operation that will use _wait_for_attribute
            mapped_cover._target_position = 70
            mapped_cover._target_tilt = 80

            # Start convergence task
            convergence_task = asyncio.create_task(mapped_cover.converge_position())
            await asyncio.sleep(0.05)  # Let it start and make some wait calls

            # Change targets to trigger event and interrupt waits
            mapped_cover._target_position = 50
            mapped_cover._target_tilt = 60

            # Trigger new convergence
            new_convergence_task = asyncio.create_task(mapped_cover.converge_position())

            # Wait for operations to complete
            await asyncio.gather(convergence_task, new_convergence_task, return_exceptions=True)

        # Should have made multiple wait calls
        assert len(wait_calls) >= 1

        # At least some calls should have been interrupted by the event
        interrupted_calls = [call for call in wait_calls if call.get('interrupted', False)]
        assert len(interrupted_calls) >= 1


class TestAsyncTaskCreation:
    """Test async task creation for converge_position doesn't block commands."""

    async def test_commands_complete_immediately_despite_convergence(self, hass, mock_config_entry):
        """Test that commands complete immediately even when convergence takes time."""
        # Set up test cover
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

        # Make convergence slow but non-blocking
        async def slow_convergence():
            """Simulate slow convergence that should not block commands."""
            await asyncio.sleep(0.2)  # 200ms delay

        with patch.object(mapped_cover, 'converge_position', side_effect=slow_convergence):
            start_time = time.time()

            # Multiple commands should complete quickly despite slow convergence
            await mapped_cover.async_set_cover_position(position=75)
            command1_time = time.time() - start_time

            await mapped_cover.async_set_cover_tilt_position(tilt_position=80)
            command2_time = time.time() - start_time

            await mapped_cover.async_open_cover()
            command3_time = time.time() - start_time

            # All commands should complete quickly (much less than convergence time)
            assert command1_time < 0.05, f"First command took too long: {command1_time}"
            assert command2_time < 0.1, f"Second command took too long: {command2_time}"
            assert command3_time < 0.15, f"Third command took too long: {command3_time}"

            # Wait a bit longer to let convergence tasks complete
            await asyncio.sleep(0.3)

    async def test_convergence_tasks_are_properly_tracked(self, hass, mock_config_entry):
        """Test that convergence tasks are properly tracked in _running_tasks."""
        # Set up test cover
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

        # Track task counts
        initial_task_count = len(mapped_cover._running_tasks)

        convergence_started = []
        convergence_finished = []

        async def track_convergence():
            """Track convergence start and finish."""
            convergence_started.append(time.time())
            await asyncio.sleep(0.05)  # Short convergence time
            convergence_finished.append(time.time())

        with patch.object(mapped_cover, 'converge_position', side_effect=track_convergence):
            # Issue multiple commands that should create tracked tasks
            await mapped_cover.async_set_cover_position(position=75)
            await mapped_cover.async_set_cover_tilt_position(tilt_position=80)

            # Tasks should be tracked
            mid_task_count = len(mapped_cover._running_tasks)
            assert mid_task_count >= initial_task_count

            # Wait for convergence to complete
            await asyncio.sleep(0.1)

            # Tasks should be removed after completion
            final_task_count = len(mapped_cover._running_tasks)

        # Multiple convergence operations should have been started
        assert len(convergence_started) >= 2

        # All should have finished
        assert len(convergence_finished) == len(convergence_started)

        # Task count should return to initial level (or lower due to cleanup)
        assert final_task_count <= initial_task_count + 1  # Allow some tolerance

    async def test_task_cleanup_on_entity_removal(self, hass, mock_config_entry):
        """Test that tasks are properly cleaned up when entity is removed."""
        # Set up test cover
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

        # Add the entity to tracked covers for proper cleanup
        self.mapped_covers = getattr(self, 'mapped_covers', [])
        self.mapped_covers.append(mapped_cover)

        task_cancelled = []

        async def long_convergence():
            """Simulate long-running convergence that can be cancelled."""
            try:
                await asyncio.sleep(1.0)  # Long operation
            except asyncio.CancelledError:
                task_cancelled.append(True)
                raise

        with patch.object(mapped_cover, 'converge_position', side_effect=long_convergence):
            # Start some long-running operations
            await mapped_cover.async_set_cover_position(position=75)
            await mapped_cover.async_set_cover_tilt_position(tilt_position=80)

            # Should have active tasks
            assert len(mapped_cover._running_tasks) >= 1

            # Simulate entity cleanup
            await mapped_cover.async_will_remove_from_hass()

            # Brief wait for cleanup to complete
            await asyncio.sleep(0.01)

            # Tasks should be cancelled and cleaned up
            assert len(mapped_cover._running_tasks) == 0

            # At least some tasks should have been cancelled
            assert len(task_cancelled) >= 1

    async def test_concurrent_convergence_tasks_do_not_interfere(self, hass, mock_config_entry):
        """Test that multiple concurrent convergence tasks do not interfere with each other."""
        # Set up test cover
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

        convergence_operations = []

        async def track_convergence_operation():
            """Track individual convergence operations."""
            operation_id = len(convergence_operations)
            operation_info = {
                'id': operation_id,
                'started': time.time(),
                'targets_at_start': (mapped_cover._target_position, mapped_cover._target_tilt),
                'aborted': False
            }
            convergence_operations.append(operation_info)

            # Simulate convergence work with abort checking
            for i in range(10):
                await asyncio.sleep(0.01)
                
                # Check if targets changed (simulating abort_check)
                current_targets = (mapped_cover._target_position, mapped_cover._target_tilt)
                if current_targets != operation_info['targets_at_start']:
                    operation_info['aborted'] = True
                    operation_info['finished'] = time.time()
                    return  # Abort this operation
                    
            operation_info['finished'] = time.time()

        with patch.object(mapped_cover, 'converge_position', side_effect=track_convergence_operation):
            # Issue rapid commands to create concurrent operations
            await mapped_cover.async_set_cover_position(position=60)  # Operation 0
            await asyncio.sleep(0.02)
            
            await mapped_cover.async_set_cover_position(position=70)  # Operation 1
            await asyncio.sleep(0.02)
            
            await mapped_cover.async_set_cover_tilt_position(tilt_position=80)  # Operation 2
            await asyncio.sleep(0.02)
            
            await mapped_cover.async_open_cover()  # Operation 3

            # Wait for all operations to complete
            await asyncio.sleep(0.2)

        # Multiple operations should have been started
        assert len(convergence_operations) >= 3

        # Earlier operations should have been aborted by target changes
        aborted_operations = [op for op in convergence_operations if op.get('aborted', False)]
        assert len(aborted_operations) >= 1

        # The last operation should have completed without abort
        if convergence_operations:
            last_operation = convergence_operations[-1]
            assert not last_operation.get('aborted', True), "Last operation should not be aborted"
            assert 'finished' in last_operation, "Last operation should have finished"
