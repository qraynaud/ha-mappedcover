from typing import Any, Dict
from unittest.mock import AsyncMock
from homeassistant.core import HomeAssistant
from tests.constants import TEST_COVER_ID, FEATURES_WITH_TILT
from tests.helpers.entities.create_unified_test_environment import create_unified_test_environment


async def create_command_test_environment(
    hass: HomeAssistant,
    entity_id: str = TEST_COVER_ID,
    current_position: int = 30,
    current_tilt_position: int = 40,
    supported_features: int = FEATURES_WITH_TILT,
    track_convergence: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """Create a test environment optimized for command testing.

    Args:
      hass: HomeAssistant instance
      entity_id: Entity ID for the source cover
      current_position: Current position of the cover
      current_tilt_position: Current tilt position
      supported_features: Supported features bitmask
      track_convergence: Whether to mock and track converge_position calls
      **kwargs: Additional arguments passed to create_unified_test_environment

    Returns:
      dict: Test environment with entity, mocks, and convergence tracking
    """
    attributes = {
        "supported_features": supported_features,
        "current_position": current_position,
        "current_tilt_position": current_tilt_position,
        "device_class": "blind"
    }
    if "attributes" in kwargs:
        attributes.update(kwargs["attributes"])
        del kwargs["attributes"]
    env = await create_unified_test_environment(
        hass,
        entity_id=entity_id,
        state="open" if current_position > 0 else "closed",
        attributes=attributes,
        **kwargs
    )
    if track_convergence:
        env["convergence_mock"] = AsyncMock()
        env["entity"].converge_position = env["convergence_mock"]
    return env
