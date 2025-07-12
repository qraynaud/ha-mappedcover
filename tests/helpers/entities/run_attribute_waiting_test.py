from homeassistant.core import HomeAssistant
from custom_components.mappedcover.cover import MappedCover
from tests.constants import (
    TEST_SCENARIO_IMMEDIATE_RETURN,
    TEST_SCENARIO_TIMEOUT,
    TEST_SCENARIO_EARLY_EXIT,
    TEST_COVER_ID,
    FEATURES_WITH_TILT,
    POSITION_MIDDLE,
    TILT_MIDDLE,
    POSITION_OPEN,
    ATTRIBUTE_WAIT_TIMEOUT,
    DEFAULT_DELAY,
)
from tests.helpers.entities.wait_for_attribute_with_state_change import wait_for_attribute_with_state_change


async def run_attribute_waiting_test(
    hass: HomeAssistant,
    config_entry,
    test_scenario: str = TEST_SCENARIO_IMMEDIATE_RETURN,
    entity_id: str = TEST_COVER_ID,
    attribute: str = "current_position",
    current_value: int = POSITION_MIDDLE,
    target_value: int = POSITION_OPEN,
    timeout: float = ATTRIBUTE_WAIT_TIMEOUT,
    compare_func=None,
    **kwargs
) -> bool:
    """Run a test for attribute waiting behavior.

    Args:
      hass: HomeAssistant instance
      config_entry: Config entry for the test
      test_scenario: Scenario to test (immediate_return, timeout, etc.)
      entity_id: Entity ID to test with
      attribute: Attribute to wait for
      current_value: Initial value of the attribute
      target_value: Target value to wait for
      timeout: Timeout for the wait
      compare_func: Optional custom comparison function
      **kwargs: Additional arguments for the test

    Returns:
      bool: True if test passed
    """
    if test_scenario == TEST_SCENARIO_IMMEDIATE_RETURN:
        current_value = target_value
    elif test_scenario == TEST_SCENARIO_TIMEOUT:
        timeout = kwargs.get("timeout", DEFAULT_DELAY)
    elif test_scenario == "unavailable_state":
        pass
    elif test_scenario == "missing_attribute":
        pass

    attrs = {
        "supported_features": FEATURES_WITH_TILT,
        "device_class": "blind"
    }
    if test_scenario != "missing_attribute":
        attrs["current_position"] = current_value if attribute == "current_position" else POSITION_MIDDLE
        attrs["current_tilt_position"] = current_value if attribute == "current_tilt_position" else TILT_MIDDLE

    state = "unavailable" if test_scenario == "unavailable_state" else "open"
    hass.states.async_set(entity_id, state, attrs)

    mapped_cover = MappedCover(hass, config_entry, entity_id)
    await mapped_cover.async_added_to_hass()

    if test_scenario == "state_change":
        result = await wait_for_attribute_with_state_change(
            mapped_cover, hass, entity_id, attribute, target_value,
            kwargs.get("intermediate_value"), timeout, compare_func
        )
    elif test_scenario == TEST_SCENARIO_EARLY_EXIT:
        import asyncio
        wait_task = asyncio.create_task(
            mapped_cover.wait_for_attribute(
                attribute, target_value, timeout, compare_func
            )
        )
        await asyncio.sleep(DEFAULT_DELAY)
        mapped_cover._target_changed_event.set()
        result = await wait_task
    else:
        result = await mapped_cover.wait_for_attribute(
            attribute, target_value, timeout, compare_func
        )
    return result
