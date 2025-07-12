from typing import Dict
from tests.helpers.config.complete_config_flow_step import complete_config_flow_step


async def complete_configure_step(hass, flow_id: str, config_data: Dict = None, include_tilt: bool = True) -> Dict:
    """Complete the configure step of config flow."""
    if config_data and not include_tilt:
        config_data = {k: v for k, v in config_data.items()
                       if not k.startswith(('min_tilt', 'max_tilt'))}
    return await complete_config_flow_step(hass, flow_id, "configure", config_data)
