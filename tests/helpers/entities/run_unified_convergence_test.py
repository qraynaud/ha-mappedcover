from typing import List, Tuple, Any
from unittest.mock import AsyncMock, patch, PropertyMock
from contextlib import ExitStack
from tests.helpers.entities.create_tracked_cover import create_tracked_cover
from tests.helpers.assertions.service_called import assert_service_called
from tests.helpers.assertions.service_not_called import assert_service_not_called
from custom_components.mappedcover.cover import MappedCover


async def run_unified_convergence_test(
    hass,
    mock_config_entry,
    current_position: int = 30,
    current_tilt_position: int = 40,
    target_position: int = None,
    target_tilt: int = None,
    is_moving: bool = False,
    expect_position_call: bool = None,
    expect_tilt_call: bool = None,
    stop_if_moving: bool = False,
    close_tilt_if_down: bool = False,
    mock_wait_for_attribute: bool = False,
    mock_sleep: bool = False
) -> Tuple[List, AsyncMock, MappedCover]:
    """Unified helper for running convergence tests with various scenarios."""
    # Set up state based on scenario
    state = "opening" if is_moving else (
        "closed" if current_position == 0 else "open")

    # Update config entry with close_tilt_if_down setting if needed
    if close_tilt_if_down:
        hass.config_entries.async_update_entry(
            mock_config_entry,
            data={**mock_config_entry.data, "close_tilt_if_down": True}
        )

    mapped_cover, call_tracker = await create_tracked_cover(
        hass,
        mock_config_entry,
        state_attrs={
            "state": state,
            "current_position": current_position,
            "current_tilt_position": current_tilt_position,
        }
    )

    # Set targets
    mapped_cover._target_position = target_position
    mapped_cover._target_tilt = target_tilt

    # Create mock call service that tracks calls
    mock_call_service = AsyncMock(
        side_effect=lambda *args, **kwargs: call_tracker.append(args[0]))

    # Set up patches based on flags
    patches = [
        patch.object(mapped_cover, '_call_service', mock_call_service),
        patch.object(mapped_cover, 'async_write_ha_state'),
        patch.object(type(mapped_cover), 'is_moving',
                     new_callable=PropertyMock, return_value=is_moving)
    ]

    # Add patches based on flags
    if stop_if_moving or mock_wait_for_attribute:
        patches.append(patch.object(
            mapped_cover, '_wait_for_attribute', new_callable=AsyncMock))
    if stop_if_moving or mock_sleep:
        patches.append(patch('asyncio.sleep', new_callable=AsyncMock))

    # Run the test with all patches
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        await mapped_cover.converge_position()

    # Verify expected calls if specified
    if expect_position_call is not None and expect_position_call:
        assert_service_called(call_tracker, "set_cover_position")
    elif expect_position_call is False:
        assert_service_not_called(call_tracker, "set_cover_position")

    if expect_tilt_call is not None and expect_tilt_call:
        assert_service_called(call_tracker, "set_cover_tilt_position")
    elif expect_tilt_call is False:
        assert_service_not_called(call_tracker, "set_cover_tilt_position")

    return call_tracker, mock_call_service, mapped_cover
