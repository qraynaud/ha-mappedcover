from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.setup import async_setup_component
from typing import List
from custom_components.mappedcover.const import DOMAIN
from tests.constants import STANDARD_CONFIG_DATA


async def create_config_flow_entry(
    hass: HomeAssistant,
    label: str = "Test Mapped Cover",
    covers: List[str] = None,
    **kwargs
) -> ConfigEntry:
    """Create a config entry through the normal config flow.

    This simulates a user creating an entry through the UI flow.

    Args:
      hass: HomeAssistant instance
      label: Label for the mapped cover
      covers: List of cover entity IDs to include
      **kwargs: Additional configuration options

    Returns:
      ConfigEntry: The created config entry
    """
    if covers is None:
        covers = ["cover.real_mappedcover"]

    await async_setup_component(hass, DOMAIN, {})

    # Create an entry using the config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    # Complete first step
    user_input_step1 = {
        "label": label,
        "covers": covers,
    }
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=user_input_step1
    )

    # Get default values
    config_data = {**STANDARD_CONFIG_DATA}

    # Override with provided kwargs
    config_data.update(kwargs)

    # Only include fields that are in the schema
    schema_str = str(result2["data_schema"]).lower()
    user_input_step2 = {k: v for k,
                        v in config_data.items() if k.lower() in schema_str}

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], user_input=user_input_step2
    )

    # Get the created entry
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    return entry
