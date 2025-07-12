from homeassistant.core import HomeAssistant
from typing import Dict
from homeassistant.setup import async_setup_component
from custom_components.mappedcover.const import DOMAIN


async def start_config_flow(hass: HomeAssistant, context: Dict = None) -> Dict:
    """Start a config flow and return the initial result.

    Args:
      hass: HomeAssistant instance
      context: Context dict for the flow (defaults to user source)

    Returns:
      The initial flow result
    """
    await async_setup_component(hass, DOMAIN, {})

    if context is None:
        context = {"source": "user"}

    return await hass.config_entries.flow.async_init(DOMAIN, context=context)
