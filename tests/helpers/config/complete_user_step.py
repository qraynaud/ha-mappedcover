from typing import Dict, List
from tests.helpers.config.complete_config_flow_step import complete_config_flow_step


async def complete_user_step(hass, flow_id: str, label: str = "Test Covers", covers: List[str] = None) -> Dict:
    """Complete the user step of config flow."""
    data = {"label": label}
    if covers is not None:
        data["covers"] = covers
    else:
        # Provide default covers if none specified (required by schema)
        data["covers"] = ["cover.real_mappedcover"]
    return await complete_config_flow_step(hass, flow_id, "user", data)
