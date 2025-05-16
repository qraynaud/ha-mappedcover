"""
Home Assistant custom component for mappedcover remapping.
"""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the mappedcover component from configuration.yaml (not used)."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up mappedcover from a config entry."""
    # Await the platform setup to avoid setup lock warnings
    await hass.config_entries.async_forward_entry_setup(entry, "cover")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_forward_entry_unload(entry, "cover")
