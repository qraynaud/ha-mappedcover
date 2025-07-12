from typing import Dict, List, Tuple
from homeassistant.config_entries import ConfigEntry
from tests.helpers.config.start_config_flow import start_config_flow
from tests.helpers.config.complete_user_step import complete_user_step
from tests.helpers.config.complete_configure_step import complete_configure_step


async def complete_full_config_flow(
    hass,
    label: str = "Test Mapped Cover",
    covers: List[str] = None,
    config_data: Dict = None
) -> Tuple[ConfigEntry, Dict]:
    """Complete a full config flow from start to finish.

    Args:
      hass: HomeAssistant instance
      label: Label for the mapped covers
      covers: List of cover entity IDs to select
      config_data: Configuration data for the configure step

    Returns:
      Tuple of (created ConfigEntry, final flow result)
    """
    # Start flow
    result = await start_config_flow(hass)

    # Complete user step
    result2 = await complete_user_step(hass, result["flow_id"], label, covers)

    # Complete configure step
    result3 = await complete_configure_step(hass, result2["flow_id"], config_data)

    # Get the created entry
    entry = hass.config_entries.async_entries("mappedcover")[0]
    return entry, result3
