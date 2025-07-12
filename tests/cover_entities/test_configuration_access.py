"""Tests for configuration property access for mappedcover."""
import pytest
import pytest_check as check
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.mappedcover.cover import MappedCover
from custom_components.mappedcover import const
from tests.helpers import create_mock_config_entry, MockThrottler
from tests.fixtures import *


class TestConfigurationPropertyAccess:
    """Test access to configuration properties through MappedCover."""

    @pytest.mark.asyncio
    async def test_rename_pattern_property_access(self, hass: HomeAssistant):
        custom_pattern = r"^Kitchen (.+)$"
        config_entry = await create_mock_config_entry(
            hass,
            rename_pattern=custom_pattern,
            rename_replacement="Smart \\1"
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._rename_pattern, custom_pattern)

    @pytest.mark.asyncio
    async def test_rename_replacement_property_access(self, hass: HomeAssistant):
        custom_replacement = "Mapped \\1 Device"
        config_entry = await create_mock_config_entry(
            hass,
            rename_pattern=r"^(.+)$",
            rename_replacement=custom_replacement
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._rename_replacement, custom_replacement)

    @pytest.mark.asyncio
    async def test_min_position_property_access(self, hass: HomeAssistant):
        custom_min_pos = 25
        config_entry = await create_mock_config_entry(
            hass,
            min_position=custom_min_pos,
            max_position=85
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._min_pos, custom_min_pos)
        check.is_true(isinstance(mapped_cover._min_pos, int))

    @pytest.mark.asyncio
    async def test_max_position_property_access(self, hass: HomeAssistant):
        custom_max_pos = 75
        config_entry = await create_mock_config_entry(
            hass,
            min_position=15,
            max_position=custom_max_pos
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._max_pos, custom_max_pos)
        check.is_true(isinstance(mapped_cover._max_pos, int))

    @pytest.mark.asyncio
    async def test_min_tilt_position_property_access(self, hass: HomeAssistant):
        custom_min_tilt = 10
        config_entry = await create_mock_config_entry(
            hass,
            min_tilt_position=custom_min_tilt,
            max_tilt_position=90
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._min_tilt, custom_min_tilt)
        check.is_true(isinstance(mapped_cover._min_tilt, int))

    @pytest.mark.asyncio
    async def test_max_tilt_position_property_access(self, hass: HomeAssistant):
        custom_max_tilt = 85
        config_entry = await create_mock_config_entry(
            hass,
            min_tilt_position=20,
            max_tilt_position=custom_max_tilt
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._max_tilt, custom_max_tilt)
        check.is_true(isinstance(mapped_cover._max_tilt, int))

    @pytest.mark.asyncio
    async def test_close_tilt_if_down_property_access(self, hass: HomeAssistant):
        config_entry_enabled = await create_mock_config_entry(
            hass,
            close_tilt_if_down=True
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover_enabled = MappedCover(
                hass, config_entry_enabled, "cover.test_cover", MockThrottler())
        check.is_true(mapped_cover_enabled._close_tilt_if_down)
        check.is_true(isinstance(
            mapped_cover_enabled._close_tilt_if_down, bool))
        config_entry_disabled = await create_mock_config_entry(
            hass,
            close_tilt_if_down=False
        )
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover_disabled = MappedCover(
                hass, config_entry_disabled, "cover.test_cover", MockThrottler())
        check.is_false(mapped_cover_disabled._close_tilt_if_down)


class TestConfigurationDefaultFallbacks:
    """Test default value fallbacks when configuration is missing."""

    @pytest.mark.asyncio
    async def test_rename_pattern_default_fallback(self, hass: HomeAssistant):
        config_entry = ConfigEntry(
            version=1,
            domain="mappedcover",
            title="Test",
            data={
                "covers": ["cover.test_cover"],
                "rename_replacement": "Custom \\1",
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
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._rename_pattern, const.DEFAULT_RENAME_PATTERN)

    @pytest.mark.asyncio
    async def test_rename_replacement_default_fallback(self, hass: HomeAssistant):
        config_entry = ConfigEntry(
            version=1,
            domain="mappedcover",
            title="Test",
            data={
                "covers": ["cover.test_cover"],
                "rename_pattern": r"^(.+)$",
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
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._rename_replacement,
                    const.DEFAULT_RENAME_REPLACEMENT)

    @pytest.mark.asyncio
    async def test_min_position_default_fallback(self, hass: HomeAssistant):
        config_entry = ConfigEntry(
            version=1,
            domain="mappedcover",
            title="Test",
            data={
                "covers": ["cover.test_cover"],
                "max_position": 90,
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
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._min_pos, const.DEFAULT_MIN_POSITION)
        check.is_true(isinstance(mapped_cover._min_pos, int))

    @pytest.mark.asyncio
    async def test_max_position_default_fallback(self, hass: HomeAssistant):
        config_entry = ConfigEntry(
            version=1,
            domain="mappedcover",
            title="Test",
            data={
                "covers": ["cover.test_cover"],
                "min_position": 10,
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
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._max_pos, const.DEFAULT_MAX_POSITION)
        check.is_true(isinstance(mapped_cover._max_pos, int))

    @pytest.mark.asyncio
    async def test_min_tilt_position_default_fallback(self, hass: HomeAssistant):
        config_entry = ConfigEntry(
            version=1,
            domain="mappedcover",
            title="Test",
            data={
                "covers": ["cover.test_cover"],
                "max_tilt_position": 95,
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
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._min_tilt, const.DEFAULT_MIN_TILT_POSITION)
        check.is_true(isinstance(mapped_cover._min_tilt, int))

    @pytest.mark.asyncio
    async def test_max_tilt_position_default_fallback(self, hass: HomeAssistant):
        config_entry = ConfigEntry(
            version=1,
            domain="mappedcover",
            title="Test",
            data={
                "covers": ["cover.test_cover"],
                "min_tilt_position": 5,
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
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._max_tilt, const.DEFAULT_MAX_TILT_POSITION)
        check.is_true(isinstance(mapped_cover._max_tilt, int))

    @pytest.mark.asyncio
    async def test_close_tilt_if_down_default_fallback(self, hass: HomeAssistant):
        config_entry = ConfigEntry(
            version=1,
            domain="mappedcover",
            title="Test",
            data={
                "covers": ["cover.test_cover"],
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
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._close_tilt_if_down,
                    const.DEFAULT_CLOSE_TILT_IF_DOWN)
        check.is_true(isinstance(mapped_cover._close_tilt_if_down, bool))


class TestConfigurationTypeConversion:
    """Test proper type conversion for configuration values."""

    @pytest.mark.asyncio
    async def test_position_values_converted_to_int(self, hass: HomeAssistant):
        config_entry = await create_mock_config_entry(
            hass,
            min_position="15",
            max_position="85"
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._min_pos, 15)
        check.equal(mapped_cover._max_pos, 85)
        check.is_true(isinstance(mapped_cover._min_pos, int))
        check.is_true(isinstance(mapped_cover._max_pos, int))

    @pytest.mark.asyncio
    async def test_tilt_values_converted_to_int(self, hass: HomeAssistant):
        config_entry = await create_mock_config_entry(
            hass,
            min_tilt_position="20",
            max_tilt_position="80"
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._min_tilt, 20)
        check.equal(mapped_cover._max_tilt, 80)
        check.is_true(isinstance(mapped_cover._min_tilt, int))
        check.is_true(isinstance(mapped_cover._max_tilt, int))

    @pytest.mark.asyncio
    async def test_close_tilt_if_down_converted_to_bool(self, hass: HomeAssistant):
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
                mapped_cover = MappedCover(
                    hass, config_entry, "cover.test_cover", MockThrottler())
            check.is_true(mapped_cover._close_tilt_if_down)
            check.is_true(isinstance(mapped_cover._close_tilt_if_down, bool))
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
                mapped_cover = MappedCover(
                    hass, config_entry, "cover.test_cover", MockThrottler())
            check.is_false(mapped_cover._close_tilt_if_down)
            check.is_true(isinstance(mapped_cover._close_tilt_if_down, bool))


class TestConfigurationEdgeCases:
    """Test edge cases and boundary conditions for configuration access."""

    @pytest.mark.asyncio
    async def test_boundary_position_values(self, hass: HomeAssistant):
        config_entry = await create_mock_config_entry(
            hass,
            min_position=0,
            max_position=100
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._min_pos, 0)
        check.equal(mapped_cover._max_pos, 100)

    @pytest.mark.asyncio
    async def test_boundary_tilt_values(self, hass: HomeAssistant):
        config_entry = await create_mock_config_entry(
            hass,
            min_tilt_position=0,
            max_tilt_position=100
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._min_tilt, 0)
        check.equal(mapped_cover._max_tilt, 100)

    @pytest.mark.asyncio
    async def test_inverted_position_range(self, hass: HomeAssistant):
        config_entry = await create_mock_config_entry(
            hass,
            min_position=80,
            max_position=20
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._min_pos, 80)
        check.equal(mapped_cover._max_pos, 20)

    @pytest.mark.asyncio
    async def test_equal_position_range(self, hass: HomeAssistant):
        config_entry = await create_mock_config_entry(
            hass,
            min_position=50,
            max_position=50
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._min_pos, 50)
        check.equal(mapped_cover._max_pos, 50)

    @pytest.mark.asyncio
    async def test_empty_rename_pattern_and_replacement(self, hass: HomeAssistant):
        config_entry = await create_mock_config_entry(
            hass,
            rename_pattern="",
            rename_replacement=""
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._rename_pattern, "")
        check.equal(mapped_cover._rename_replacement, "")

    @pytest.mark.asyncio
    async def test_configuration_with_all_custom_values(self, hass: HomeAssistant):
        config_entry = await create_mock_config_entry(
            hass,
            rename_pattern=r"^Kitchen (.+) Blinds$",
            rename_replacement=r"Smart \\1 Controller",
            min_position=15,
            max_position=85,
            min_tilt_position=10,
            max_tilt_position=90,
            close_tilt_if_down=False,
            throttle=200
        )
        hass.states.async_set("cover.test_cover", "closed", {})
        with patch("custom_components.mappedcover.cover.Throttler", MockThrottler):
            mapped_cover = MappedCover(
                hass, config_entry, "cover.test_cover", MockThrottler())
        check.equal(mapped_cover._rename_pattern, r"^Kitchen (.+) Blinds$")
        check.equal(mapped_cover._rename_replacement, r"Smart \\1 Controller")
        check.equal(mapped_cover._min_pos, 15)
        check.equal(mapped_cover._max_pos, 85)
        check.equal(mapped_cover._min_tilt, 10)
        check.equal(mapped_cover._max_tilt, 90)
        check.is_false(mapped_cover._close_tilt_if_down)
        check.is_true(isinstance(mapped_cover._min_pos, int))
        check.is_true(isinstance(mapped_cover._max_pos, int))
        check.is_true(isinstance(mapped_cover._min_tilt, int))
        check.is_true(isinstance(mapped_cover._max_tilt, int))
        check.is_true(isinstance(mapped_cover._close_tilt_if_down, bool))
