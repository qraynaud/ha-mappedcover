from tests.constants import FEATURES_WITH_TILT


def create_mock_cover_entity(
    hass,
    entity_id,
    state="closed",
    supported_features=None,
    current_position=0,
    current_tilt_position=0,
    device_class="blind",
    attributes=None,
    **kwargs
):
    """Create a mock cover entity with standard attributes.

    Args:
      hass: HomeAssistant instance
      entity_id: The entity_id to create
      state: The state of the cover (open, closed, etc.)
      supported_features: Bitmask of supported features
      current_position: Current position (0-100)
      current_tilt_position: Current tilt position (0-100)
      device_class: Device class of the cover
      attributes: Optional dictionary with additional attributes to set
      **kwargs: Additional attributes (for backward compatibility)
    """
    if supported_features is None:
        supported_features = FEATURES_WITH_TILT

    default_attributes = {
        "supported_features": supported_features,
        "current_position": current_position,
        "current_tilt_position": current_tilt_position,
        "device_class": device_class
    }

    if attributes:
        default_attributes.update(attributes)
    if kwargs:
        default_attributes.update(kwargs)

    hass.states.async_set(
        entity_id,
        state,
        default_attributes
    )
