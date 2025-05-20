"""
Config flow for mappedcover integration.
"""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import entity_registry
from homeassistant.helpers.selector import selector
from homeassistant.config_entries import SOURCE_RECONFIGURE
import logging

from . import const

_LOGGER = logging.getLogger(__name__)

def supports_tilt(hass, entity_id):
  try:
    state = hass.states.get(entity_id)
    if state and "supported_features" in state.attributes:
      supported_features = state.attributes["supported_features"]
      return bool(supported_features & (16 | 128))
  except Exception as exc:
    _LOGGER.warning("Could not determine tilt support: %s", exc)
  return False

def build_remap_schema(tilt_supported, data=None):
  data = data or {}
  schema_dict = {
    vol.Required("rename_pattern", default=data.get("rename_pattern")): str,
    vol.Required("rename_replacement", default=data.get("rename_replacement")): str,
    vol.Required("min_position", default=data.get("min_position")): vol.All(int, vol.Range(min=0, max=100)),
    vol.Required("max_position", default=data.get("max_position")): vol.All(int, vol.Range(min=0, max=100)),
  }
  if tilt_supported:
    schema_dict[vol.Required("min_tilt_position", default=data.get("min_tilt_position"))] = vol.All(int, vol.Range(min=0, max=100))
    schema_dict[vol.Required("max_tilt_position", default=data.get("max_tilt_position"))] = vol.All(int, vol.Range(min=0, max=100))
  schema_dict[vol.Optional("close_tilt_if_down", default=data.get("close_tilt_if_down"))] = bool
  return vol.Schema(schema_dict)

class MappedCoverConfigFlow(config_entries.ConfigFlow, domain=const.DOMAIN):
  """Handle a config flow for mappedcover."""

  VERSION = 1

  def __init__(self):
    """Initialize the config flow."""
    super().__init__()
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
    }

  async def async_step_user(self, user_input=None):
    """Step 1: Select the source cover entity."""
    _LOGGER.debug("Starting async_step_user with user_input: %s", user_input)
    if user_input is not None:
      # Proceed to configure step with selected entity
      self._data.update(user_input)
      _LOGGER.debug("Going to configure with data=%s", self._data)
      return await self.async_step_configure()

    errors = {}
    try:
      entity_reg = entity_registry.async_get(self.hass)
      covers = []
      for entity in entity_reg.entities.values():
        if entity.platform == const.DOMAIN:
          covers.append(entity.entity_id)
      _LOGGER.debug("Found covers to exclude: %s", covers)
    except Exception as exc:
      _LOGGER.error("Error while fetching covers: %s", exc, exc_info=True)
      return self.async_abort(reason="internal_error")

    schema = vol.Schema({
      vol.Required("label", default=self._data["label"]): str,
      vol.Required("covers", default=self._data["covers"]): vol.All(
        selector({
          "entity": {
            "multiple": True,
            "exclude_entities": covers,
            "filter": { "domain": "cover" },
          },
        }),
        vol.Length(min=1),
      )
    })

    _LOGGER.debug("Showing form for entity selection")
    return self.async_show_form(
      step_id="user",
      data_schema=schema,
      errors=errors,
    )

  async def async_step_configure(self, user_input=None):
    """Unified step for both configure and reconfigure."""
    errors = {}

    if self.source == SOURCE_RECONFIGURE:
      entry = self._get_reconfigure_entry()
      if entry.unique_id:
        await self.async_set_unique_id(entry.unique_id)
        self._abort_if_unique_id_mismatch()

    if user_input is not None:
      self._data.update(user_input)
      _LOGGER.debug("Updating entry with: %s", self._data)

      title = self._data["label"]
      data = self._data.copy()
      del data["label"]

      if self.source == SOURCE_RECONFIGURE:
        return self.async_update_reload_and_abort(
          entry=entry,
          title=title,
          data=data,
        )
      else:
        return self.async_create_entry(title=title, data=data)

    tilt_supported = False
    try:
      for cover in self._data["covers"]:
        tilt_supported = supports_tilt(self.hass, cover)
        if tilt_supported:
          break
    except Exception as exc:
      _LOGGER.warning("Could not determine tilt support: %s", exc)

    schema = build_remap_schema(
      tilt_supported=tilt_supported,
      data=self._data,
    )

    _LOGGER.debug("Showing configure form...")
    return self.async_show_form(
      step_id="configure",
      data_schema=schema,
      errors=errors,
    )

  async def async_step_reconfigure(self, user_input=None):
    entry = self._get_reconfigure_entry()
    self._data.update(entry.data)
    self._data["label"] = entry.title
    # For reconfigure, redirect to user step
    return await self.async_step_user(user_input)
