from typing import Tuple
from unittest.mock import patch, PropertyMock, AsyncMock, MagicMock
from custom_components.mappedcover.cover import MappedCover
from tests.helpers.mocks.throttler import MockThrottler
from tests.constants import TEST_COVER_ID, FEATURES_WITH_TILT


async def run_abort_logic_test(
    hass,
    mock_config_entry,
    change_position_target: bool = True,
    change_tilt_target: bool = False,
    call_to_change_at: int = 1
) -> Tuple[int, MappedCover]:
    """Run a test for abort logic when targets change during execution."""
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

    # Set initial targets
    mapped_cover._target_position = 70
    mapped_cover._target_tilt = 80

    call_count = 0

    async def change_target_during_execution(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == call_to_change_at:
            if change_position_target:
                mapped_cover._target_position = 50
            if change_tilt_target:
                mapped_cover._target_tilt = 90

    with patch.object(mapped_cover, '_call_service', side_effect=change_target_during_execution), \
            patch.object(mapped_cover, 'async_write_ha_state'), \
            patch.object(type(mapped_cover), 'is_moving', new_callable=PropertyMock, return_value=False):
        await mapped_cover.converge_position()

    return call_count, mapped_cover
