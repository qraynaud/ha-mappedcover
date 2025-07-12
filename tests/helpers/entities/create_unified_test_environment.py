from typing import Any, Dict
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.core import HomeAssistant
from tests.constants import TEST_COVER_ID, FEATURES_WITH_TILT, STANDARD_CONFIG_DATA
from tests.helpers.config.mock_config_entry import create_mock_config_entry
from tests.helpers.entities.registry_mocks import setup_mock_registries
from tests.helpers.mocks.throttler import MockThrottler
from custom_components.mappedcover.cover import MappedCover


async def create_unified_test_environment(
    hass: HomeAssistant,
    entity_id: str = TEST_COVER_ID,
    state: str = "closed",
    attributes: Dict[str, Any] = None,
    config_data: Dict[str, Any] = None,
    mock_registry: bool = False,
    track_calls: bool = False,
    mock_service_calls: bool = False,
    mock_throttler: bool = True,
    return_mocks: bool = True
) -> Dict[str, Any]:
    """Create a unified test environment combining functionality of multiple helpers.

    Args:
      hass: HomeAssistant instance
      entity_id: Entity ID for the source cover
      state: Initial state of the entity
      attributes: Entity attributes (defaults to standard cover attributes)
      config_data: Custom config data (defaults to STANDARD_CONFIG_DATA)
      mock_registry: Whether to set up mock registries
      track_calls: Whether to track service calls
      mock_service_calls: Whether to mock the _call_service method
      mock_throttler: Whether to mock the throttler
      return_mocks: Whether to return mock objects

    Returns:
      dict: Environment with all test components
    """
    if attributes is None:
        attributes = {
            "supported_features": FEATURES_WITH_TILT,
            "current_position": 0 if state == "closed" else 50,
            "current_tilt_position": 0 if state == "closed" else 40,
            "device_class": "blind"
        }

    hass.states.async_set(entity_id, state, attributes)

    if config_data is None:
        config_data = STANDARD_CONFIG_DATA.copy()

    config_entry = await create_mock_config_entry(
        hass,
        covers=[entity_id],
        **config_data
    )

    registries = None
    if mock_registry:
        registries = await setup_mock_registries(
            hass,
            config_entry,
            source_entity_id=entity_id
        )

    call_tracker = []
    service_mock = None
    throttler_mock = None

    if mock_throttler:
        throttler_mock = MagicMock()
        throttler_mock.__aenter__ = AsyncMock()
        throttler_mock.__aexit__ = AsyncMock()
    else:
        throttler_mock = MockThrottler()

    with patch("custom_components.mappedcover.cover.Throttler", return_value=throttler_mock):
        entity = MappedCover(hass, config_entry, entity_id, throttler_mock)

    async_write_ha_state_mock = MagicMock()
    entity.async_write_ha_state = async_write_ha_state_mock

    if track_calls or mock_service_calls:
        async def track_service_calls(service_name, service_data=None, **kwargs):
            call_tracker.append((service_name, service_data))
        if mock_service_calls:
            service_mock = AsyncMock(side_effect=track_service_calls)
            entity._call_service = service_mock

    result = {
        "entity": entity,
        "config_entry": config_entry,
        "hass": hass,
        "call_tracker": call_tracker,
        "async_write_ha_state_mock": async_write_ha_state_mock,
    }

    if registries:
        result["registries"] = registries

    if return_mocks:
        if service_mock:
            result["service_mock"] = service_mock
        if mock_throttler:
            result["throttler_mock"] = throttler_mock

    return result
