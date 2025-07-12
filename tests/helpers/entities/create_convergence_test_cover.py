from unittest.mock import patch
from tests.helpers.mocks.throttler import MockThrottler
from custom_components.mappedcover.cover import MappedCover
from tests.constants import FEATURES_WITH_TILT, TEST_COVER_ID


async def create_convergence_test_cover(
    hass,
    mock_config_entry,
    entity_id: str = TEST_COVER_ID,
    **state_attrs
) -> MappedCover:
    """Create a MappedCover for convergence testing with default attributes."""
    default_attrs = {
        "state": "open",
        "supported_features": FEATURES_WITH_TILT,
        "current_position": 30,
        "current_tilt_position": 40,
        "device_class": "blind"
    }
    default_attrs.update(state_attrs)

    state = default_attrs.pop("state")

    hass.states.async_set(entity_id, state, default_attrs)

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        return MappedCover(hass, mock_config_entry, entity_id, MockThrottler())
