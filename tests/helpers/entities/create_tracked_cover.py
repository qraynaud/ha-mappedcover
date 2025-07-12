from typing import Dict, Tuple
from tests.constants import TEST_COVER_ID
from custom_components.mappedcover.cover import MappedCover
from unittest.mock import AsyncMock
from tests.helpers.entities.create_convergence_test_cover import create_convergence_test_cover


async def create_tracked_cover(
    hass,
    mock_config_entry,
    entity_id: str = TEST_COVER_ID,
    state_attrs: Dict = None
) -> Tuple[MappedCover, list]:
    """Create a MappedCover with call tracking for testing."""
    if state_attrs is None:
        state_attrs = {
            "state": "open",
            "current_position": 30,
            "current_tilt_position": 40
        }

    mapped_cover = await create_convergence_test_cover(
        hass, mock_config_entry, entity_id, **state_attrs
    )

    call_tracker = []

    # Patch _call_service to track calls
    mapped_cover._call_service = AsyncMock(
        side_effect=lambda service, **kwargs: call_tracker.append((service, kwargs)))

    return mapped_cover, call_tracker
