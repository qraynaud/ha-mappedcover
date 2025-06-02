"""Test integration setup and basic functionality."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


def test_manifest_exists():
  """Test that the integration manifest file exists."""
  import os
  assert os.path.exists("custom_components/mappedcover/manifest.json")


async def test_integration_can_be_loaded(hass: HomeAssistant):
  """Test that Home Assistant can load the integration."""
  from homeassistant.loader import async_get_integration
  integration = await async_get_integration(hass, "mappedcover")
  assert integration is not None
  assert integration.domain == "mappedcover"


async def test_integration_setup(hass: HomeAssistant):
  """Test that the integration can be set up."""
  # This should work without errors - the integration should load
  result = await async_setup_component(hass, "mappedcover", {})
  assert result is True
