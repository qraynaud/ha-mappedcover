from tests.helpers.entities.mock_cover_entity import create_mock_cover_entity


def create_standard_mock_covers(hass):
    """Create standard mock cover entities used across tests.

    This creates a set of standard cover entities with various states
    that can be referenced by tests.

    Args:
      hass: HomeAssistant instance
    """
    create_mock_cover_entity(
        hass,
        "cover.real_mappedcover",
        state="closed",
        attributes={"device_class": "mappedcover"}
    )
    create_mock_cover_entity(
        hass,
        "cover.another_mappedcover",
        state="open",
        attributes={"device_class": "blind"}
    )
    create_mock_cover_entity(
        hass,
        "cover.mapped_mappedcover_1",
        state="closed",
        attributes={"device_class": "mappedcover"}
    )
