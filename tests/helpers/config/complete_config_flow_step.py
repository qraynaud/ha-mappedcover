from typing import Dict
from tests.constants import STANDARD_CONFIG_DATA


async def complete_config_flow_step(
    hass,
    flow_id: str,
    step_type: str = "user",
    data: Dict = None,
    **kwargs
) -> Dict:
    """Complete a config flow step with provided data.

    This unified helper replaces complete_user_step and complete_configure_step.

    Args:
      hass: HomeAssistant instance
      flow_id: The flow ID
      step_type: Type of step ("user", "configure", "reconfigure")
      data: Data to submit (if None, uses defaults based on step_type)
      **kwargs: Override specific fields in the default data

    Returns:
      The result of completing the step
    """
    if data is None:
        if step_type == "user":
            data = {
                "label": "Test Covers",
                "covers": ["cover.real_mappedcover"],
            }
        elif step_type in ("configure", "reconfigure"):
            data = {**STANDARD_CONFIG_DATA}
        else:
            data = {}

    # Override with any provided kwargs
    data.update(kwargs)

    return await hass.config_entries.flow.async_configure(flow_id, user_input=data)
