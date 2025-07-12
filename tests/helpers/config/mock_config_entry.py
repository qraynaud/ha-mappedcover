from homeassistant.config_entries import ConfigEntry
from tests.constants import TEST_ENTRY_ID, TEST_COVER_ID, STANDARD_CONFIG_DATA
from custom_components.mappedcover.const import DOMAIN


async def create_mock_config_entry(
    hass,
    entry_id: str = TEST_ENTRY_ID,
    title: str = "Test Mapped Cover",
    covers=None,
    **kwargs
) -> ConfigEntry:
    """Create a mock config entry with standard test data.

    Args:
      hass: HomeAssistant instance
      entry_id: Unique ID for the config entry
      title: Title for the config entry
      covers: List of cover entity IDs to include
      **kwargs: Additional configuration options to override defaults

    Returns:
      ConfigEntry: The created config entry
    """
    if covers is None:
        covers = [TEST_COVER_ID]

    data = {
        "covers": covers,
        **STANDARD_CONFIG_DATA
    }
    data.update(kwargs)

    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title=title,
        data=data,
        source="user",
        options={},
        unique_id=entry_id,
        minor_version=1,
        discovery_keys=[],
        subentries_data={}
    )

    await hass.config_entries.async_add(entry)
    return entry
