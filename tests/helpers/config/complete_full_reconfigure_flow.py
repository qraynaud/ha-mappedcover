from typing import Dict, List
from homeassistant.config_entries import ConfigEntry
from tests.helpers.config.start_reconfigure_flow import start_reconfigure_flow
from tests.helpers.config.complete_user_step import complete_user_step
from tests.helpers.config.complete_configure_step import complete_configure_step


async def complete_full_reconfigure_flow(
    hass,
    config_entry: ConfigEntry,
    label: str = "Updated Label",
    covers: List[str] = None,
    config_data: Dict = None
) -> Dict:
    """Complete a full reconfigure flow from start to finish.

    Args:
      hass: HomeAssistant instance
      config_entry: The existing config entry to reconfigure
      label: New label for the mapped covers
      covers: New list of cover entity IDs to select
      config_data: New configuration data

    Returns:
      The final reconfigure flow result
    """
    # Start reconfigure flow
    result = await start_reconfigure_flow(hass, config_entry)

    # Complete user step
    result2 = await complete_user_step(hass, result["flow_id"], label, covers)

    # Complete configure step
    result3 = await complete_configure_step(hass, result2["flow_id"], config_data)

    return result3
