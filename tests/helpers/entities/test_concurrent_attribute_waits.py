from homeassistant.core import HomeAssistant
from tests.constants import TEST_COVER_ID
from tests.helpers.entities.test_cover_with_throttler import create_test_cover_with_throttler
from tests.fixtures import *


async def test_concurrent_attribute_waits(
    hass: HomeAssistant,
    mock_config_entry,
    entity_id: str = TEST_COVER_ID
):
    """Test multiple concurrent wait_for_attribute calls.

    Args:
      hass: HomeAssistant instance
      mock_config_entry: Config entry to use
      entity_id: Entity ID to test with

    Returns:
      Tuple of (results, mapped_cover, cover_manager)
    """
    import asyncio
    hass.states.async_set(
        entity_id,
        "open",
        {
            "supported_features": 143,
            "current_position": 30,
            "current_tilt_position": 40,
            "device_class": "blind"
        }
    )
    mapped_cover, _ = create_test_cover_with_throttler(
        hass, mock_config_entry, entity_id)
    wait_task1 = asyncio.create_task(
        mapped_cover._wait_for_attribute("current_position", 70, timeout=5)
    )
    wait_task2 = asyncio.create_task(
        mapped_cover._wait_for_attribute(
            "current_tilt_position", 80, timeout=5)
    )
    await asyncio.sleep(0.1)
    hass.states.async_set(
        entity_id,
        "open",
        {
            "supported_features": 143,
            "current_position": 70,
            "current_tilt_position": 40,
            "device_class": "blind"
        }
    )
    result1 = await wait_task1
    hass.states.async_set(
        entity_id,
        "open",
        {
            "supported_features": 143,
            "current_position": 70,
            "current_tilt_position": 80,
            "device_class": "blind"
        }
    )
    result2 = await wait_task2
    return (result1, result2), mapped_cover, None
