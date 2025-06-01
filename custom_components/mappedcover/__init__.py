"""
Home Assistant custom component for mappedcover remapping.
"""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up mappedcover from a config entry."""
    # Await the platform setup to avoid setup lock warnings
    await hass.config_entries.async_forward_entry_setups(entry, ["cover"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
  """Unload a config entry."""
  unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "cover")

  # In your component's async_unload_entry function
  if entry.entry_id in hass.data.get(DOMAIN, {}):
    del hass.data[DOMAIN][entry.entry_id]
    if not hass.data[DOMAIN]:  # Remove domain if empty
      hass.data.pop(DOMAIN, None)

  return unload_ok
