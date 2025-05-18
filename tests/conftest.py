import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
  """Automatically enable loading custom integrations in all tests."""
  yield
