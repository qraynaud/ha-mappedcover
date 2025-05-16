import pytest
from unittest.mock import patch
from homeassistant import data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

# Constants for test
DOMAIN = "mappedcover"

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

@pytest.fixture
async def mock_cover_entities(hass: HomeAssistant):
  """Set up mock mappedcover entities in the state machine."""
  hass.states.async_set("cover.real_mappedcover", "closed", {"supported_features": 15, "device_class": "mappedcover"})
  hass.states.async_set("cover.another_mappedcover", "open", {"supported_features": 15, "device_class": "blind"})
  hass.states.async_set("cover.mapped_mappedcover_1", "closed", {"supported_features": 15, "device_class": "mappedcover"})
  yield

def test_integration_manifest_exists():
  import os
  assert os.path.exists("custom_components/mappedcover/manifest.json")

async def test_loader_can_find_integration(hass):
  from homeassistant.loader import async_get_integration
  integration = await async_get_integration(hass, "mappedcover")
  assert integration is not None

async def test_config_flow_shows_required_fields(hass, mock_cover_entities):
  """Test that the config flow UI displays all required fields."""
  await async_setup_component(hass, DOMAIN, {})
  result = await hass.config_entries.flow.async_init(
      DOMAIN, context={"source": "user"}
  )
  assert result["type"] == "form"
  data_schema = result["data_schema"]
  # Should have at least entity, name, id, min/max position
  fields = str(data_schema).lower()
  assert "entity" in fields or "cover" in fields
  assert "name" in fields
  assert "id" in fields
  assert "min" in fields and "max" in fields

async def test_config_flow_excludes_mapped_covers(hass, mock_cover_entities):
  """Test that only valid, non-mapped cover entities are selectable."""
  await async_setup_component(hass, DOMAIN, {})
  result = await hass.config_entries.flow.async_init(
      DOMAIN, context={"source": "user"}
  )
  # The form should not offer cover.mapped_cover_1 as a choice
  data_schema = result["data_schema"]
  # This is a bit indirect, but we can check the entity list
  entity_choices = str(data_schema).lower()
  assert "cover.mapped_cover_1" not in entity_choices
  assert "cover.real_cover" in entity_choices
  assert "cover.another_cover" in entity_choices

async def test_config_flow_creates_entry_with_correct_data(hass, mock_cover_entities):
  """Test that submitting the config flow creates an entry with the correct data."""
  await async_setup_component(hass, DOMAIN, {})
  result = await hass.config_entries.flow.async_init(
      DOMAIN, context={"source": "user"}
  )
  # Simulate user input
  user_input = {
      "cover_entity": "cover.real_cover",
      "mapped_cover_name": "Test Mapped Cover",
      "mapped_cover_id": "test_mapped_cover",
      "min_position": 0,
      "max_position": 100,
      "min_tilt_position": 0,
      "max_tilt_position": 100,
  }
  result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=user_input)
  assert result2["type"] == "create_entry"
  data = result2["data"]
  assert data["cover_entity"] == "cover.real_cover"
  assert data["mapped_cover_name"] == "Test Mapped Cover"
  assert data["mapped_cover_id"] == "test_mapped_cover"
  assert data["min_position"] == 0
  assert data["max_position"] == 100
  assert data["min_tilt_position"] == 0
  assert data["max_tilt_position"] == 100

async def test_config_flow_validates_min_max(hass, mock_cover_entities):
  """Test that min/max values are validated and stored as expected."""
  await async_setup_component(hass, DOMAIN, {})
  result = await hass.config_entries.flow.async_init(
      DOMAIN, context={"source": "user"}
  )
  # Simulate user input with invalid min/max
  user_input = {
      "cover_entity": "cover.real_cover",
      "mapped_cover_name": "Test Mapped Cover",
      "mapped_cover_id": "test_mapped_cover",
      "min_position": 100,
      "max_position": 0,
      "min_tilt_position": 100,
      "max_tilt_position": 0,
  }
  result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=user_input)
  # Should return a form with errors
  assert result2["type"] == "form"
  assert "errors" in result2

async def test_config_flow_tilt_options_only_if_supported(hass, mock_cover_entities):
  """Test that tilt options are only shown if the selected entity supports tilt."""
  # Patch the state to not support tilt
  hass.states.async_set("cover.no_tilt_cover", "closed", {"supported_features": 3})
  await async_setup_component(hass, DOMAIN, {})
  result = await hass.config_entries.flow.async_init(
      DOMAIN, context={"source": "user"}
  )
  # Simulate user selecting the no-tilt cover
  user_input = {
      "cover_entity": "cover.no_tilt_cover",
      "mapped_cover_name": "No Tilt Mapped",
      "mapped_cover_id": "no_tilt_mapped",
      "min_position": 0,
      "max_position": 100,
  }
  result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=user_input)
  # Should create entry without tilt options
  assert result2["type"] == "create_entry"
  data = result2["data"]
  assert "min_tilt_position" not in data or data["min_tilt_position"] == 0
  assert "max_tilt_position" not in data or data["max_tilt_position"] == 100
