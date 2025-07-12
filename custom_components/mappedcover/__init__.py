"""
Home Assistant custom component for mappedcover remapping.

This integration allows mapping cover position and tilt values from source covers
to different ranges, enabling unified control of covers with varying position scales.
The main functionality is implemented in the cover platform.
"""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up mappedcover from a config entry.

    This function is called by Home Assistant when the integration is being
    loaded. It forwards the setup to the cover platform where the actual
    entity creation happens.

    Args:
      hass: Home Assistant instance
      entry: ConfigEntry containing the integration configuration

    Returns:
      bool: True if setup was successful
    """
    print("async_setup_entry, %s", entry)
    # Forward setup to cover platform - await to prevent setup lock warnings
    await hass.config_entries.async_forward_entry_setups(entry, ["cover"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry and clean up integration data.

    This function is called when the integration is being unloaded or
    reconfigured. It ensures proper cleanup of the cover platform and
    any stored data.

    Args:
      hass: Home Assistant instance
      entry: ConfigEntry being unloaded

    Returns:
      bool: True if unload was successful
    """
    # Unload the cover platform
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "cover")

    # Clean up any stored data for this config entry
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        del hass.data[DOMAIN][entry.entry_id]
        # Remove domain from hass.data if no entries remain
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)

    return unload_ok
