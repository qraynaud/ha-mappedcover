from homeassistant.core import HomeAssistant
from typing import Any


async def wait_for_attribute_with_state_change(
    mapped_cover: Any,
    hass: HomeAssistant,
    entity_id: str,
    attribute: str,
    target_value: int,
    intermediate_value: int = None,
    timeout: float = 5.0,
    compare=None,
    compare_func=None
):
    """Test waiting for attribute with optional state change during wait.

    Args:
      mapped_cover: The MappedCover instance to test
      hass: HomeAssistant instance
      entity_id: Entity ID to update
      attribute: Attribute to wait for
      target_value: Target value to wait for
      intermediate_value: Optional intermediate value to set first
      timeout: Timeout for the wait
      compare: Optional comparison function
      compare_func: Optional comparison function (overrides compare)

    Returns:
      Result of the wait_for_attribute call
    """
    import asyncio
    compare_to_use = compare_func or compare
    if compare_to_use:
        wait_task = asyncio.create_task(
            mapped_cover._wait_for_attribute(
                attribute, target_value, timeout=timeout, compare=compare_to_use)
        )
    else:
        wait_task = asyncio.create_task(
            mapped_cover._wait_for_attribute(
                attribute, target_value, timeout=timeout)
        )
    await asyncio.sleep(0.1)
    if intermediate_value is not None:
        current_state = hass.states.get(entity_id)
        attrs = dict(current_state.attributes)
        attrs[attribute] = intermediate_value
        hass.states.async_set(entity_id, current_state.state, attrs)
        await asyncio.sleep(0.1)
    current_state = hass.states.get(entity_id)
    attrs = dict(current_state.attributes)
    attrs[attribute] = target_value
    hass.states.async_set(entity_id, current_state.state, attrs)
    return await wait_task
