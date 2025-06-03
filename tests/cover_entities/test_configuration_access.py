"""Test configuration property access for mappedcover."""
import pytest
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.mappedcover.cover import MappedCover
from custom_components.mappedcover import const
from tests.helpers import MockThrottler, create_mock_config_entry


class TestConfigurationPropertyAccess:
  """Test access to configuration properties through MappedCover."""

  async def test_rename_pattern_property_access(self, hass: HomeAssistant):
    """Test property access for rename_pattern configuration value."""
    custom_pattern = r"^Kitchen (.+)$"

    config_entry = await create_mock_config_entry(
      hass,
      rename_pattern=custom_pattern,
      rename_replacement="Smart \\1"
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._rename_pattern == custom_pattern

  async def test_rename_replacement_property_access(self, hass: HomeAssistant):
    """Test property access for rename_replacement configuration value."""
    custom_replacement = "Mapped \\1 Device"

    config_entry = await create_mock_config_entry(
      hass,
      rename_pattern=r"^(.+)$",
      rename_replacement=custom_replacement
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._rename_replacement == custom_replacement

  async def test_min_position_property_access(self, hass: HomeAssistant):
    """Test property access for min_position configuration value."""
    custom_min_pos = 25

    config_entry = await create_mock_config_entry(
      hass,
      min_position=custom_min_pos,
      max_position=85
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._min_pos == custom_min_pos
    assert isinstance(mapped_cover._min_pos, int)

  async def test_max_position_property_access(self, hass: HomeAssistant):
    """Test property access for max_position configuration value."""
    custom_max_pos = 75

    config_entry = await create_mock_config_entry(
      hass,
      min_position=15,
      max_position=custom_max_pos
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._max_pos == custom_max_pos
    assert isinstance(mapped_cover._max_pos, int)

  async def test_min_tilt_position_property_access(self, hass: HomeAssistant):
    """Test property access for min_tilt_position configuration value."""
    custom_min_tilt = 10

    config_entry = await create_mock_config_entry(
      hass,
      min_tilt_position=custom_min_tilt,
      max_tilt_position=90
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._min_tilt == custom_min_tilt
    assert isinstance(mapped_cover._min_tilt, int)

  async def test_max_tilt_position_property_access(self, hass: HomeAssistant):
    """Test property access for max_tilt_position configuration value."""
    custom_max_tilt = 85

    config_entry = await create_mock_config_entry(
      hass,
      min_tilt_position=20,
      max_tilt_position=custom_max_tilt
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._max_tilt == custom_max_tilt
    assert isinstance(mapped_cover._max_tilt, int)

  async def test_close_tilt_if_down_property_access(self, hass: HomeAssistant):
    """Test property access for close_tilt_if_down configuration flag."""
    # Test with feature enabled
    config_entry_enabled = await create_mock_config_entry(
      hass,
      close_tilt_if_down=True
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover_enabled = MappedCover(hass, config_entry_enabled, "cover.test_cover", MockThrottler())

    assert mapped_cover_enabled._close_tilt_if_down is True
    assert isinstance(mapped_cover_enabled._close_tilt_if_down, bool)

    # Test with feature disabled
    config_entry_disabled = await create_mock_config_entry(
      hass,
      close_tilt_if_down=False
    )

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover_disabled = MappedCover(hass, config_entry_disabled, "cover.test_cover", MockThrottler())

    assert mapped_cover_disabled._close_tilt_if_down is False


class TestConfigurationDefaultFallbacks:
  """Test default value fallbacks when configuration is missing."""

  async def test_rename_pattern_default_fallback(self, hass: HomeAssistant):
    """Test rename_pattern falls back to default when missing from config."""
    # Create config entry without rename_pattern
    config_entry = ConfigEntry(
      version=1,
      domain="mappedcover",
      title="Test",
      data={
        "covers": ["cover.test_cover"],
        "rename_replacement": "Custom \\1",
        # Missing rename_pattern
      },
      source="user",
      options={},
      unique_id="test_entry",
      minor_version=1,
      discovery_keys=[],
      subentries_data={}
    )
    await hass.config_entries.async_add(config_entry)

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._rename_pattern == const.DEFAULT_RENAME_PATTERN

  async def test_rename_replacement_default_fallback(self, hass: HomeAssistant):
    """Test rename_replacement falls back to default when missing from config."""
    # Create config entry without rename_replacement
    config_entry = ConfigEntry(
      version=1,
      domain="mappedcover",
      title="Test",
      data={
        "covers": ["cover.test_cover"],
        "rename_pattern": r"^(.+)$",
        # Missing rename_replacement
      },
      source="user",
      options={},
      unique_id="test_entry",
      minor_version=1,
      discovery_keys=[],
      subentries_data={}
    )
    await hass.config_entries.async_add(config_entry)

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._rename_replacement == const.DEFAULT_RENAME_REPLACEMENT

  async def test_min_position_default_fallback(self, hass: HomeAssistant):
    """Test min_position falls back to default when missing from config."""
    config_entry = ConfigEntry(
      version=1,
      domain="mappedcover",
      title="Test",
      data={
        "covers": ["cover.test_cover"],
        "max_position": 90,
        # Missing min_position
      },
      source="user",
      options={},
      unique_id="test_entry",
      minor_version=1,
      discovery_keys=[],
      subentries_data={}
    )
    await hass.config_entries.async_add(config_entry)

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._min_pos == const.DEFAULT_MIN_POSITION
    assert isinstance(mapped_cover._min_pos, int)

  async def test_max_position_default_fallback(self, hass: HomeAssistant):
    """Test max_position falls back to default when missing from config."""
    config_entry = ConfigEntry(
      version=1,
      domain="mappedcover",
      title="Test",
      data={
        "covers": ["cover.test_cover"],
        "min_position": 10,
        # Missing max_position
      },
      source="user",
      options={},
      unique_id="test_entry",
      minor_version=1,
      discovery_keys=[],
      subentries_data={}
    )
    await hass.config_entries.async_add(config_entry)

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._max_pos == const.DEFAULT_MAX_POSITION
    assert isinstance(mapped_cover._max_pos, int)

  async def test_min_tilt_position_default_fallback(self, hass: HomeAssistant):
    """Test min_tilt_position falls back to default when missing from config."""
    config_entry = ConfigEntry(
      version=1,
      domain="mappedcover",
      title="Test",
      data={
        "covers": ["cover.test_cover"],
        "max_tilt_position": 95,
        # Missing min_tilt_position
      },
      source="user",
      options={},
      unique_id="test_entry",
      minor_version=1,
      discovery_keys=[],
      subentries_data={}
    )
    await hass.config_entries.async_add(config_entry)

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._min_tilt == const.DEFAULT_MIN_TILT_POSITION
    assert isinstance(mapped_cover._min_tilt, int)

  async def test_max_tilt_position_default_fallback(self, hass: HomeAssistant):
    """Test max_tilt_position falls back to default when missing from config."""
    config_entry = ConfigEntry(
      version=1,
      domain="mappedcover",
      title="Test",
      data={
        "covers": ["cover.test_cover"],
        "min_tilt_position": 5,
        # Missing max_tilt_position
      },
      source="user",
      options={},
      unique_id="test_entry",
      minor_version=1,
      discovery_keys=[],
      subentries_data={}
    )
    await hass.config_entries.async_add(config_entry)

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._max_tilt == const.DEFAULT_MAX_TILT_POSITION
    assert isinstance(mapped_cover._max_tilt, int)

  async def test_close_tilt_if_down_default_fallback(self, hass: HomeAssistant):
    """Test close_tilt_if_down falls back to default when missing from config."""
    config_entry = ConfigEntry(
      version=1,
      domain="mappedcover",
      title="Test",
      data={
        "covers": ["cover.test_cover"],
        # Missing close_tilt_if_down
      },
      source="user",
      options={},
      unique_id="test_entry",
      minor_version=1,
      discovery_keys=[],
      subentries_data={}
    )
    await hass.config_entries.async_add(config_entry)

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._close_tilt_if_down == const.DEFAULT_CLOSE_TILT_IF_DOWN
    assert isinstance(mapped_cover._close_tilt_if_down, bool)


class TestConfigurationTypeConversion:
  """Test proper type conversion for configuration values."""

  async def test_position_values_converted_to_int(self, hass: HomeAssistant):
    """Test that position configuration values are properly converted to integers."""
    config_entry = await create_mock_config_entry(
      hass,
      min_position="15",  # String values that should be converted to int
      max_position="85"
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._min_pos == 15
    assert mapped_cover._max_pos == 85
    assert isinstance(mapped_cover._min_pos, int)
    assert isinstance(mapped_cover._max_pos, int)

  async def test_tilt_values_converted_to_int(self, hass: HomeAssistant):
    """Test that tilt configuration values are properly converted to integers."""
    config_entry = await create_mock_config_entry(
      hass,
      min_tilt_position="20",  # String values that should be converted to int
      max_tilt_position="80"
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._min_tilt == 20
    assert mapped_cover._max_tilt == 80
    assert isinstance(mapped_cover._min_tilt, int)
    assert isinstance(mapped_cover._max_tilt, int)

  async def test_close_tilt_if_down_converted_to_bool(self, hass: HomeAssistant):
    """Test that close_tilt_if_down configuration is properly converted to boolean."""
    # Test with truthy values
    for truthy_value in [1, "true", "yes", "on"]:
      config_entry = ConfigEntry(
        version=1,
        domain="mappedcover",
        title="Test",
        data={
          "covers": ["cover.test_cover"],
          "close_tilt_if_down": truthy_value,
        },
        source="user",
        options={},
        unique_id=f"test_entry_{truthy_value}",
        minor_version=1,
        discovery_keys=[],
        subentries_data={}
      )
      await hass.config_entries.async_add(config_entry)

      with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

      assert mapped_cover._close_tilt_if_down is True
      assert isinstance(mapped_cover._close_tilt_if_down, bool)

    # Test with falsy values
    for falsy_value in [0, False, "", None]:
      config_entry = ConfigEntry(
        version=1,
        domain="mappedcover",
        title="Test",
        data={
          "covers": ["cover.test_cover"],
          "close_tilt_if_down": falsy_value,
        },
        source="user",
        options={},
        unique_id=f"test_entry_{falsy_value}",
        minor_version=1,
        discovery_keys=[],
        subentries_data={}
      )
      await hass.config_entries.async_add(config_entry)

      with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
        mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

      assert mapped_cover._close_tilt_if_down is False
      assert isinstance(mapped_cover._close_tilt_if_down, bool)


class TestConfigurationEdgeCases:
  """Test edge cases and boundary conditions for configuration access."""

  async def test_boundary_position_values(self, hass: HomeAssistant):
    """Test configuration access with boundary position values (0 and 100)."""
    config_entry = await create_mock_config_entry(
      hass,
      min_position=0,    # Boundary minimum
      max_position=100   # Boundary maximum
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._min_pos == 0
    assert mapped_cover._max_pos == 100

  async def test_boundary_tilt_values(self, hass: HomeAssistant):
    """Test configuration access with boundary tilt values (0 and 100)."""
    config_entry = await create_mock_config_entry(
      hass,
      min_tilt_position=0,    # Boundary minimum
      max_tilt_position=100   # Boundary maximum
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._min_tilt == 0
    assert mapped_cover._max_tilt == 100

  async def test_inverted_position_range(self, hass: HomeAssistant):
    """Test configuration access when min_position > max_position (edge case)."""
    config_entry = await create_mock_config_entry(
      hass,
      min_position=80,  # Inverted range
      max_position=20
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    # Values should be returned as configured, even if inverted
    assert mapped_cover._min_pos == 80
    assert mapped_cover._max_pos == 20

  async def test_equal_position_range(self, hass: HomeAssistant):
    """Test configuration access when min_position equals max_position."""
    config_entry = await create_mock_config_entry(
      hass,
      min_position=50,  # Equal range
      max_position=50
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._min_pos == 50
    assert mapped_cover._max_pos == 50

  async def test_empty_rename_pattern_and_replacement(self, hass: HomeAssistant):
    """Test configuration access with empty rename pattern and replacement."""
    config_entry = await create_mock_config_entry(
      hass,
      rename_pattern="",     # Empty pattern
      rename_replacement=""  # Empty replacement
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    assert mapped_cover._rename_pattern == ""
    assert mapped_cover._rename_replacement == ""

  async def test_configuration_with_all_custom_values(self, hass: HomeAssistant):
    """Test comprehensive configuration access with all custom values."""
    config_entry = await create_mock_config_entry(
      hass,
      rename_pattern=r"^Kitchen (.+) Blinds$",
      rename_replacement=r"Smart \1 Controller",
      min_position=15,
      max_position=85,
      min_tilt_position=10,
      max_tilt_position=90,
      close_tilt_if_down=False,
      throttle=200
    )

    hass.states.async_set("cover.test_cover", "closed", {})

    with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
      mapped_cover = MappedCover(hass, config_entry, "cover.test_cover", MockThrottler())

    # Verify all configuration values are accessible
    assert mapped_cover._rename_pattern == r"^Kitchen (.+) Blinds$"
    assert mapped_cover._rename_replacement == r"Smart \1 Controller"
    assert mapped_cover._min_pos == 15
    assert mapped_cover._max_pos == 85
    assert mapped_cover._min_tilt == 10
    assert mapped_cover._max_tilt == 90
    assert mapped_cover._close_tilt_if_down is False

    # Verify proper type conversion
    assert isinstance(mapped_cover._min_pos, int)
    assert isinstance(mapped_cover._max_pos, int)
    assert isinstance(mapped_cover._min_tilt, int)
    assert isinstance(mapped_cover._max_tilt, int)
    assert isinstance(mapped_cover._close_tilt_if_down, bool)
