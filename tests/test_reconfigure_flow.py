import pytest
from unittest.mock import patch, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_RECONFIGURE

DOMAIN = "mappedcover"

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

@pytest.fixture
async def config_entry(hass, mock_cover_entities):
    """Create a config entry for mappedcover through the normal flow."""
    await async_setup_component(hass, DOMAIN, {})

    # Create an entry using the config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    # Complete first step
    user_input_step1 = {
        "label": "Test Mapped Cover",
        "covers": ["cover.real_mappedcover"],
    }
    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=user_input_step1)

    # Complete second step with basic data (let defaults handle tilt if supported)
    user_input_step2 = {
        "rename_pattern": "^(.*)$",
        "rename_replacement": "Mapped \\1",
        "min_position": 10,
        "max_position": 90,
        "close_tilt_if_down": True,
        "throttle": 150,
    }
    # Only add tilt fields if the schema supports them
    schema_str = str(result2["data_schema"]).lower()
    if "min_tilt_position" in schema_str:
        user_input_step2.update({
            "min_tilt_position": 5,
            "max_tilt_position": 95,
        })
    result3 = await hass.config_entries.flow.async_configure(result2["flow_id"], user_input=user_input_step2)

    # Get the created entry
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    return entry

@pytest.fixture
async def mock_cover_entities(hass: HomeAssistant):
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers import device_registry as dr

    # First create the state without device connection
    hass.states.async_set("cover.real_mappedcover", "closed", {"supported_features": 143, "device_class": "mappedcover"})
    yield

async def test_reconfigure_flow_can_be_started(hass, config_entry, mock_cover_entities):
    """Test that the reconfigure flow can be started for an existing mapped cover."""
    # Start reconfigure flow properly with the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
        data=None
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    # Should show a form with the correct schema
    assert result["data_schema"] is not None

async def test_reconfigure_flow_allows_modification(hass, config_entry, mock_cover_entities):
    """Test that the reconfigure flow shows existing values and allows modification."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
        data=None
    )

    # Complete first step with modifications
    user_input_step1 = {
        "label": "Updated Label",
        "covers": ["cover.real_mappedcover"],
    }
    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=user_input_step1)

    # Complete second step with modifications
    user_input_step2 = {
        "rename_pattern": "^Cover (.*)$",
        "rename_replacement": "Window \\1",
        "min_position": 20,
        "max_position": 80,
        "min_tilt_position": 10,
        "max_tilt_position": 90,
        "close_tilt_if_down": False,
        "throttle": 200,
    }
    result3 = await hass.config_entries.flow.async_configure(result2["flow_id"], user_input=user_input_step2)
    assert result3["type"] == "abort"
    assert result3["reason"] == "reconfigure_successful"

async def test_reconfigure_flow_applies_changes(hass, config_entry, mock_cover_entities):
    """Test that reconfigure flow successfully applies changes."""
    # Capture the original entry state
    original_title = config_entry.title
    original_min_position = config_entry.data.get("min_position", 0)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
        data=None
    )

    # Complete first step
    user_input_step1 = {
        "label": "Reloaded Label",
        "covers": ["cover.real_mappedcover"],
    }
    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=user_input_step1)

    # Complete second step with different values
    user_input_step2 = {
        "rename_pattern": "^(.*)$",
        "rename_replacement": "Mapped \\1",
        "min_position": 15,
        "max_position": 85,
        "min_tilt_position": 5,
        "max_tilt_position": 95,
        "close_tilt_if_down": True,
        "throttle": 150,
    }
    result3 = await hass.config_entries.flow.async_configure(result2["flow_id"], user_input=user_input_step2)

    # Verify the flow completed successfully with reconfigure_successful
    assert result3["type"] == "abort"
    assert result3["reason"] == "reconfigure_successful"

    # Verify changes were applied to the config entry
    assert config_entry.title == "Reloaded Label"
    assert config_entry.data["min_position"] == 15

async def test_reconfigure_flow_persists_changes(hass, config_entry, mock_cover_entities):
    """Test that changes persist after reconfiguration."""
    original_title = config_entry.title
    original_data = config_entry.data.copy()

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
        data=None
    )

    # Complete first step with new label
    user_input_step1 = {
        "label": "Persistent Label",
        "covers": ["cover.real_mappedcover"],
    }
    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=user_input_step1)

    # Complete second step with new values
    user_input_step2 = {
        "rename_pattern": "^(.*)$",
        "rename_replacement": "Mapped \\1",
        "min_position": 30,
        "max_position": 70,
        "min_tilt_position": 10,
        "max_tilt_position": 90,
        "close_tilt_if_down": False,
        "throttle": 100,
    }
    await hass.config_entries.flow.async_configure(result2["flow_id"], user_input=user_input_step2)

    # Verify changes were applied (title should change to new label)
    assert config_entry.title == "Persistent Label"
    assert config_entry.data["min_position"] == 30
    assert config_entry.data["throttle"] == 100

async def test_reconfigure_flow_unique_id_handling(hass, config_entry, mock_cover_entities):
    """Test reconfigure step with unique_id handling."""
    # Set a unique_id on the entry first
    hass.config_entries.async_update_entry(config_entry, unique_id="test_unique_id")

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
        data=None
    )

    # The flow should handle unique_id correctly and not abort
    assert result["type"] == "form"
    assert result["step_id"] == "user"

async def test_reconfigure_flow_preserves_entry_data_structure(hass, config_entry, mock_cover_entities):
    """Test reconfigure preserves existing entry data structure."""
    original_entry_id = config_entry.entry_id
    original_domain = config_entry.domain

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
        data=None
    )

    # Complete both steps
    user_input_step1 = {
        "label": "Preserved Structure",
        "covers": ["cover.real_mappedcover"],
    }
    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=user_input_step1)

    user_input_step2 = {
        "rename_pattern": "^(.*)$",
        "rename_replacement": "Mapped \\1",
        "min_position": 10,
        "max_position": 90,
        "min_tilt_position": 5,
        "max_tilt_position": 95,
        "close_tilt_if_down": True,
        "throttle": 150,
    }
    await hass.config_entries.flow.async_configure(result2["flow_id"], user_input=user_input_step2)

    # Entry ID and domain should remain unchanged
    assert config_entry.entry_id == original_entry_id
    assert config_entry.domain == original_domain

async def test_reconfigure_flow_redirects_through_user_step(hass, config_entry, mock_cover_entities):
    """Test reconfigure redirects through user step correctly."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
        data=None
    )

    # Should start with user step for reconfigure
    assert result["type"] == "form"
    assert result["step_id"] == "user"

async def test_reconfigure_vs_new_entry_code_paths(hass, config_entry, mock_cover_entities):
    """Test reconfigure vs new entry code paths in async_step_configure."""
    # Test the reconfigure path
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
        data=None
    )

    user_input_step1 = {
        "label": "Code Path Test",
        "covers": ["cover.real_mappedcover"],
    }
    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=user_input_step1)

    user_input_step2 = {
        "rename_pattern": "^(.*)$",
        "rename_replacement": "Mapped \\1",
        "min_position": 10,
        "max_position": 90,
        "min_tilt_position": 5,
        "max_tilt_position": 95,
        "close_tilt_if_down": True,
        "throttle": 150,
    }
    result3 = await hass.config_entries.flow.async_configure(result2["flow_id"], user_input=user_input_step2)

    # Reconfigure should use abort with reconfigure_successful
    assert result3["type"] == "abort"
    assert result3["reason"] == "reconfigure_successful"
