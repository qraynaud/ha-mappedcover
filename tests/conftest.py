import pytest
import shutil
import os
from pathlib import Path

pytest_plugins = ["pytest_homeassistant_custom_component"]

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
  """Automatically enable loading custom integrations in all tests."""
  yield

@pytest.fixture(autouse=True)
def copy_custom_components_to_test_config(hass):
  """Copy our custom components to the test config directory."""
  # Get the project root directory (where this test file is)
  project_root = Path(__file__).parent.parent
  source_custom_components = project_root / "custom_components"

  # Get the test config directory from hass
  test_config_dir = Path(hass.config.config_dir)
  target_custom_components = test_config_dir / "custom_components"

  # Ensure target directory exists
  target_custom_components.mkdir(exist_ok=True)

  # Copy our mappedcover integration
  source_mappedcover = source_custom_components / "mappedcover"
  target_mappedcover = target_custom_components / "mappedcover"

  # Only copy if source exists and target doesn't already exist
  if source_mappedcover.exists() and not target_mappedcover.exists():
    shutil.copytree(source_mappedcover, target_mappedcover)
    copied = True
  else:
    copied = False

  yield

  # Cleanup after test (only if we copied)
  if copied and target_mappedcover.exists():
    shutil.rmtree(target_mappedcover)
