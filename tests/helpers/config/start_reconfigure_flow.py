from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from typing import Dict
from custom_components.mappedcover.const import DOMAIN


async def start_reconfigure_flow(hass: HomeAssistant, config_entry: ConfigEntry) -> Dict:
    """Start a reconfigure flow for an existing config entry.

    Args:
      hass: HomeAssistant instance
      config_entry: The existing config entry to reconfigure

    Returns:
      The initial reconfigure flow result
    """
    from homeassistant.config_entries import SOURCE_RECONFIGURE

    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE,
                 "entry_id": config_entry.entry_id},
        data=None
    )
