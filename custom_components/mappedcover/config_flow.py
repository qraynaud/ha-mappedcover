"""
Config flow for mappedcover integration.
"""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry
from homeassistant.helpers import device_registry
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def get_display_name(entity, dev_reg):
    device_name = None
    if entity and entity.device_id:
        device = dev_reg.async_get(entity.device_id)
        if device and device.name:
            device_name = device.name
    return device_name or (entity.original_name if entity else None) or (entity.entity_id if entity else None)

def supports_tilt(hass, entity_id):
    try:
        state = hass.states.get(entity_id)
        if state and "supported_features" in state.attributes:
            supported_features = state.attributes["supported_features"]
            return bool(supported_features & (16 | 128))
    except Exception as exc:
        _LOGGER.warning("Could not determine tilt support: %s", exc)
    return False

def build_remap_schema(*, default_name, default_id, default_min, default_max, tilt_supported, data=None):
    data = data or {}
    schema_dict = {
        vol.Required("cover_name", default=data.get("cover_name", default_name)): str,
        vol.Required("min_position", default=data.get("min_position", default_min)): vol.All(int, vol.Range(min=0, max=100)),
        vol.Required("max_position", default=data.get("max_position", default_max)): vol.All(int, vol.Range(min=0, max=100)),
    }
    if tilt_supported:
        schema_dict[vol.Required("min_tilt_position", default=data.get("min_tilt_position", default_min))] = vol.All(int, vol.Range(min=0, max=100))
        schema_dict[vol.Required("max_tilt_position", default=data.get("max_tilt_position", default_max))] = vol.All(int, vol.Range(min=0, max=100))
    return vol.Schema(schema_dict)

class MappedCoverConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for mappedcover."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Step 1: Select the source cover entity."""
        _LOGGER.debug("Starting async_step_user with user_input: %s", user_input)
        errors = {}
        try:
            entity_reg = entity_registry.async_get(self.hass)
            dev_reg = device_registry.async_get(self.hass)
            covers = []
            for entity in entity_reg.entities.values():
                if entity.entity_id.startswith("cover.") and not entity.entity_id.startswith(f"cover.{DOMAIN}_"):
                    display_name = get_display_name(entity, dev_reg)
                    covers.append((entity.entity_id, display_name))
            covers.sort(key=lambda x: x[1].lower())
            entity_id_to_display = {entity_id: display_name for entity_id, display_name in covers}
            _LOGGER.debug("Found covers: %s", covers)
        except Exception as exc:
            _LOGGER.error("Error while fetching covers: %s", exc, exc_info=True)
            return self.async_abort(reason="internal_error")

        if not entity_id_to_display:
            _LOGGER.warning("No covers found, aborting config flow.")
            return self.async_abort(reason="no_covers_found")

        default_entity_id = next(iter(entity_id_to_display.keys()))

        if user_input is not None:
            # Proceed to next step with selected entity
            return await self.async_step_configure_remap({"cover_entity": user_input["cover_entity"]})

        schema = vol.Schema({
            vol.Required("cover_entity"): vol.In(entity_id_to_display),
        })
        _LOGGER.debug("Showing form for entity selection with schema: %s", schema)
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_configure_remap(self, user_input=None):
        """Step 2: Configure mapped entity name, id, and remapping options."""
        errors = {}
        # Retrieve selected entity from previous step
        if user_input is not None and "cover_entity" in user_input:
            cover_entity = user_input["cover_entity"]
            self._selected_entity_id = cover_entity
        else:
            cover_entity = getattr(self, "_selected_entity_id", None)
        if not cover_entity:
            errors["base"] = "internal_error"
            return self.async_show_form(
                step_id="user",
                errors=errors,
            )
        if user_input is not None and "cover_name" in user_input:
            # Final step, create entry
            entry = {
                "cover_entity": cover_entity,
                "cover_name": user_input["cover_name"],
                "min_position": user_input["min_position"],
                "max_position": user_input["max_position"],
            }
            min_tilt = user_input.get("min_tilt_position")
            max_tilt = user_input.get("max_tilt_position")
            if min_tilt is not None and max_tilt is not None:
                entry["min_tilt_position"] = min_tilt
                entry["max_tilt_position"] = max_tilt
            _LOGGER.debug("Creating entry with: %s", entry)
            return self.async_create_entry(title=entry["cover_name"], data=entry)

        entity_reg = entity_registry.async_get(self.hass)
        dev_reg = device_registry.async_get(self.hass)
        entity = entity_reg.entities.get(cover_entity)
        display_name = get_display_name(entity, dev_reg)
        default_id = f"mapped_{cover_entity.split('.', 1)[-1]}"
        default_name = f"Mapped {display_name}"
        # Default min/max
        default_min = 0
        default_max = 100
        tilt_supported = supports_tilt(self.hass, cover_entity)
        schema = build_remap_schema(
            default_name=default_name,
            default_id=default_id,
            default_min=default_min,
            default_max=default_max,
            tilt_supported=tilt_supported,
        )
        _LOGGER.debug("Showing form for name/id/remap with schema: %s", schema)
        return self.async_show_form(
            step_id="configure_remap",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MappedCoverOptionsFlow(config_entry)

class MappedCoverOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        # Get current values from options or fall back to config entry data
        data = self.config_entry.options or self.config_entry.data
        cover_entity = data.get("cover_entity")
        # Defensive: if cover_entity is None, try to recover from config entry data
        if not cover_entity:
            cover_entity = self.config_entry.data.get("cover_entity")
        if not cover_entity:
            errors["base"] = "internal_error"
            return self.async_show_form(
                step_id="init",
                data_schema=build_remap_schema(
                    default_name=data.get("cover_name", ""),
                    default_id=data.get("cover_id", ""),
                    default_min=data.get("min_position", 0),
                    default_max=data.get("max_position", 100),
                    tilt_supported=False,
                    data=data,
                ),
                errors=errors,
            )
        try:
            tilt_supported = supports_tilt(self.hass, cover_entity)
        except Exception as exc:
            _LOGGER.warning("Could not determine tilt support: %s", exc)
            tilt_supported = False
        schema = build_remap_schema(
            default_name=data.get("cover_name", ""),
            default_id=data.get("cover_id", ""),
            default_min=data.get("min_position", 0),
            default_max=data.get("max_position", 100),
            tilt_supported=tilt_supported,
            data=data,
        )
        if user_input is not None:
            options = dict(user_input)
            new_name = options["cover_name"]
            self.hass.config_entries.async_update_entry(
                self.config_entry, title=new_name
            )
            # Always include cover_entity in the options
            options["cover_entity"] = cover_entity
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
