"""Fixture for mock_source_cover_state for mappedcover tests."""
import pytest
from homeassistant.core import HomeAssistant
from tests.constants import TEST_COVER_ID


@pytest.fixture
def mock_source_cover_state(hass: HomeAssistant):
    """Create a mock state for the source cover entity."""
    hass.states.async_set(
        TEST_COVER_ID,
        "closed",
        {
            "supported_features": 143,  # Support position and tilt
            "current_position": 0,
            "current_tilt_position": 0,
            "device_class": "blind"
        }
    )
