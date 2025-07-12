"""Fixture for cleanup_timers for mappedcover tests."""
import pytest
from homeassistant.core import HomeAssistant
from tests.helpers import cleanup_platform_timers


@pytest.fixture(autouse=True)
async def cleanup_timers(hass: HomeAssistant):
    """Automatically cleanup platform timers after each test."""
    yield
    await cleanup_platform_timers(hass)
