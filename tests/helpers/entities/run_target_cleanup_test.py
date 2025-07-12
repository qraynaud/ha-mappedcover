from typing import Tuple
from unittest.mock import patch, PropertyMock, AsyncMock, MagicMock
from custom_components.mappedcover.cover import MappedCover
from tests.helpers.mocks.throttler import MockThrottler
from tests.constants import TEST_COVER_ID, FEATURES_WITH_TILT


async def run_target_cleanup_test(
    hass,
    mock_config_entry,
    set_position_target: bool = True,
    set_tilt_target: bool = True,
    abort_during_execution: bool = False
) -> Tuple[MappedCover, MagicMock]:
    """Run a test for target cleanup after convergence completion."""
    hass.states.async_set(
        TEST_COVER_ID,
        "open",
        {
            "supported_features": FEATURES_WITH_TILT,
            "current_position": 30,
            "current_tilt_position": 40,
            "device_class": "blind"
        }
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler), \
            patch("custom_components.mappedcover.cover.MappedCover._wait_for_attribute", return_value=True):
        mapped_cover = MappedCover(
            hass, mock_config_entry, TEST_COVER_ID, MockThrottler())

    # Set specified targets
    mapped_cover._target_position = 70 if set_position_target else None
    mapped_cover._target_tilt = 80 if set_tilt_target else None

    # Create side effect to abort if needed
    if abort_during_execution:
        mock_call_service = AsyncMock(
            side_effect=lambda *args, **kwargs: setattr(mapped_cover, '_target_position', 50))
    else:
        mock_call_service = AsyncMock()

    mock_write_state = MagicMock()

    # Store original event for cleanup
    original_event = mapped_cover._target_changed_event
    # Mock the event to prevent lingering tasks
    mapped_cover._target_changed_event = MagicMock()
    mapped_cover._target_changed_event.set = MagicMock()
    mapped_cover._target_changed_event.wait = AsyncMock()

    try:
        # Apply all necessary patches in one context manager block
        with patch.object(mapped_cover, '_call_service', mock_call_service), \
                patch.object(mapped_cover, 'async_write_ha_state', mock_write_state), \
                patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):
            await mapped_cover.converge_position()
        return mapped_cover, mock_write_state
    finally:
        # Restore the original event to ensure proper cleanup
        mapped_cover._target_changed_event = original_event
