"""Test integration setup and basic functionality.

This module tests the integration's basic setup, manifest file, and loading.
"""
import os
import pytest_check as check
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.loader import async_get_integration


def test_manifest_exists():
    """Test that the integration manifest file exists."""
    check.is_true(os.path.exists(
        "custom_components/mappedcover/manifest.json"))


async def test_integration_can_be_loaded(hass: HomeAssistant):
    """Test that Home Assistant can load the integration."""
    integration = await async_get_integration(hass, "mappedcover")
    check.is_true(integration is not None)
    check.equal(integration.domain, "mappedcover")


async def test_integration_setup(hass: HomeAssistant):
    """Test that the integration can be set up."""
    # This should work without errors - the integration should load
    result = await async_setup_component(hass, "mappedcover", {})
    check.is_true(result)
