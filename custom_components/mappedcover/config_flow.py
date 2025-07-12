"""
Config flow for mappedcover integration.

This module handles the UI configuration flow for setting up mapped covers.
It provides a two-step process: first selecting source covers, then configuring
the remapping parameters and naming options.
"""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import entity_registry
from homeassistant.helpers.selector import selector
from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.components.cover import CoverEntityFeature
import logging

from . import const

_LOGGER = logging.getLogger(__name__)


def supports_tilt(hass, entity_id):
    """
    Check if a cover entity supports tilt operations.

    Examines the supported_features attribute to determine if the cover
    can perform tilt operations (open/close tilt or set tilt position).

    Args:
      hass: Home Assistant instance
      entity_id: Entity ID of the cover to check

    Returns:
      bool: True if the cover supports tilt operations
    """
    try:
        state = hass.states.get(entity_id)
        if state and "supported_features" in state.attributes:
            supported_features = state.attributes["supported_features"]
            # Check for any tilt-related features using bitwise AND
            return bool(supported_features & (CoverEntityFeature.OPEN_TILT | CoverEntityFeature.SET_TILT_POSITION))
    except Exception as exc:
        _LOGGER.warning(
            "Could not determine tilt support for %s: %s", entity_id, exc)
    return False


def build_remap_schema(tilt_supported, data=None):
    """
    Build the configuration schema based on whether tilt is supported.

    Creates a dynamic form schema that includes tilt options only when
    at least one selected cover supports tilt operations.

    Args:
      tilt_supported: Whether any selected covers support tilt
      data: Existing configuration data for default values

    Returns:
      vol.Schema: Voluptuous schema for the configuration form
    """
    data = data or {}
    schema_dict = {
        vol.Required("rename_pattern", default=data.get("rename_pattern")): str,
        vol.Required("rename_replacement", default=data.get("rename_replacement")): str,
        vol.Required("min_position", default=data.get("min_position")): vol.All(int, vol.Range(min=0, max=100)),
        vol.Required("max_position", default=data.get("max_position")): vol.All(int, vol.Range(min=0, max=100)),
    }

    # Add tilt configuration options only if any cover supports tilt
    if tilt_supported:
        schema_dict[vol.Required("min_tilt_position", default=data.get(
            "min_tilt_position"))] = vol.All(int, vol.Range(min=0, max=100))
        schema_dict[vol.Required("max_tilt_position", default=data.get(
            "max_tilt_position"))] = vol.All(int, vol.Range(min=0, max=100))
        schema_dict[vol.Optional(
            "close_tilt_if_down", default=data.get("close_tilt_if_down"))] = bool

    # Optional settings that apply regardless of tilt support
    schema_dict[vol.Optional("throttle", default=data.get(
        "throttle", const.DEFAULT_THROTTLE))] = int
    return vol.Schema(schema_dict)


class MappedCoverConfigFlow(config_entries.ConfigFlow, domain=const.DOMAIN):
    """
    Handle configuration flow for mappedcover integration.

    This config flow provides a two-step setup process:
    1. Select source cover entities to be mapped
    2. Configure remapping parameters and naming options

    The flow also handles reconfiguration of existing entries.
    """

    VERSION = 1

    def __init__(self):
        """Initialize the config flow with default values."""
        super().__init__()
        # Default configuration values loaded from constants
        self._data = {
            "label": const.DEFAULT_LABEL,
            "covers": [],
            "rename_pattern": const.DEFAULT_RENAME_PATTERN,
            "rename_replacement": const.DEFAULT_RENAME_REPLACEMENT,
            "min_position": const.DEFAULT_MIN_POSITION,
            "max_position": const.DEFAULT_MAX_POSITION,
            "min_tilt_position": const.DEFAULT_MIN_TILT_POSITION,
            "max_tilt_position": const.DEFAULT_MAX_TILT_POSITION,
            "close_tilt_if_down": const.DEFAULT_CLOSE_TILT_IF_DOWN,
            "throttle": const.DEFAULT_THROTTLE,
        }

    async def async_step_user(self, user_input=None):
        """
        First step: Select source cover entities to be mapped.

        Presents a form allowing users to select multiple cover entities
        and specify a label for the integration instance. Excludes any
        covers that are already managed by this integration to prevent
        circular references.

        Args:
          user_input: Form data from the user, or None for initial display

        Returns:
          FlowResult: Either shows the form or proceeds to configure step
        """
        _LOGGER.debug(
            "Starting async_step_user with user_input: %s", user_input)
        if user_input is not None:
            # User has selected covers, proceed to configuration step
            self._data.update(user_input)
            _LOGGER.debug("Going to configure with data=%s", self._data)
            return await self.async_step_configure()

        try:
            # Find existing mapped covers to exclude from selection
            entity_reg = entity_registry.async_get(self.hass)
            covers = [entity.entity_id for entity in entity_reg.entities.values(
            ) if entity.platform == const.DOMAIN]
            _LOGGER.debug("Found covers to exclude: %s", covers)
        except Exception as exc:
            _LOGGER.error("Error while fetching covers: %s",
                          exc, exc_info=True)
            return self.async_abort(reason="internal_error")

        # Build form schema for cover selection
        schema = vol.Schema({
            vol.Required("label", default=self._data["label"]): str,
            vol.Required("covers", default=self._data["covers"]): vol.All(
                selector({
                    "entity": {
                        "multiple": True,
                        "exclude_entities": covers,  # Prevent selecting existing mapped covers
                        "filter": {"domain": "cover"},
                    },
                }),
                vol.Length(min=1),  # Require at least one cover
            )
        })

        _LOGGER.debug("Showing form for entity selection")
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors={},
        )

    async def async_step_configure(self, user_input=None):
        """
        Second step: Configure remapping parameters and create/update entry.

        This step handles both initial configuration and reconfiguration.
        It dynamically shows tilt options only if any selected covers support
        tilt operations, and creates or updates the config entry.

        Args:
          user_input: Form data from the user, or None for initial display

        Returns:
          FlowResult: Either shows the form or creates/updates the entry
        """
        # Handle reconfiguration flow setup
        if self.source == SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
            if entry.unique_id:
                await self.async_set_unique_id(entry.unique_id)
                self._abort_if_unique_id_mismatch()

        if user_input is not None:
            # User has submitted configuration, create or update entry
            self._data.update(user_input)
            _LOGGER.debug("Updating entry with: %s", self._data)
            title = self._data["label"]
            data = self._data.copy()
            del data["label"]  # Title is stored separately from data

            if self.source == SOURCE_RECONFIGURE:
                return self.async_update_reload_and_abort(
                    entry=entry,
                    title=title,
                    data=data,
                )
            else:
                return self.async_create_entry(title=title, data=data)

        # Check if any selected covers support tilt to show relevant options
        tilt_supported = any(supports_tilt(self.hass, cover)
                             for cover in self._data["covers"])
        schema = build_remap_schema(
            tilt_supported=tilt_supported,
            data=self._data,
        )
        _LOGGER.debug("Showing configure form...")
        return self.async_show_form(
            step_id="configure",
            data_schema=schema,
            errors={},
        )

    async def async_step_reconfigure(self, user_input=None):
        """
        Handle reconfiguration of an existing config entry.

        Loads the existing configuration data and redirects to the user step
        to allow modification of all settings including cover selection.

        Args:
          user_input: Form data (unused in this step)

        Returns:
          FlowResult: Redirects to user step with existing data loaded
        """
        entry = self._get_reconfigure_entry()
        self._data.update(entry.data)
        self._data["label"] = entry.title
        # Redirect to user step for reconfiguration
        return await self.async_step_user(user_input)
