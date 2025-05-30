"""
Cover platform for mappedcover integration.
"""
import logging
from enum import Enum
import asyncio
import time
import re
from homeassistant.components.cover import (
  CoverEntity,
  CoverEntityFeature,
  CoverState,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers import entity_registry
from homeassistant.helpers import device_registry
from homeassistant.core import callback
from . import const
from homeassistant.config_entries import ConfigEntry
from asyncio_throttle import Throttler

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
  """Set up the mapped cover from a config entry."""
  covers = entry.data.get("covers", [])
  throttle = entry.data.get("throttle", const.DEFAULT_THROTTLE)
  throttler = Throttler(1, throttle / 1000)
  ent_reg = entity_registry.async_get(hass)
  dev_reg = device_registry.async_get(hass)

  # Remove outdated entities
  for entity in list(ent_reg.entities.values()):
    if (
      entity.platform == const.DOMAIN
      and entity.config_entry_id == entry.entry_id
      and entity.entity_id not in [f"cover.{cover}" for cover in covers]
    ):
      ent_reg.async_remove(entity.entity_id)
      dev_reg.async_remove_device(entity.device_id)

  mapped_entities = []
  for cover in covers:
    mapped_entities.append(MappedCover(hass, entry, cover, throttler))
  async_add_entities(mapped_entities)

  # After entities are added, set their area_id only if not already set
  for mapped_entity in mapped_entities:
    src_entity = ent_reg.async_get(mapped_entity._source_entity_id)
    src_device = dev_reg.async_get(src_entity.device_id)
    area_id = (src_device and src_device.area_id) or (src_entity and src_entity.area_id)
    if area_id:
      mapped_reg_entity = ent_reg.async_get(mapped_entity.entity_id)
      mapped_device = dev_reg.async_get(mapped_reg_entity.device_id)
      if mapped_device:
        dev_reg.async_update_device(mapped_device.id, area_id=area_id)

async def async_unload_entry(hass, entry):
  """Unload a config entry."""
  # Unload all entities
  _LOGGER.debug("Unloading entry: %s − covers: %s", entry.entry_id, entry.data.get("covers", []))
  ent_reg = entity_registry.async_get(hass)
  dev_reg = device_registry.async_get(hass)

  for cover in entry.data.get("covers", []):
    entity = ent_reg.async_get(cover)
    ent_reg.async_remove(entity.entity_id)
    dev_reg.async_remove_device(entity.device_id)
  return True

async def async_remove_entry(hass, entry):
  """Remove a config entry."""
  return async_unload_entry(hass, entry)

class RemapDirection(Enum):
  TO_SOURCE = 1
  FROM_SOURCE = 2

def remap_value(value, min_value, max_value, direction=RemapDirection.TO_SOURCE):
  """
  Remap a value between the user scale (0-100) and the source scale (min_value..max_value).

  - RemapDirection.TO_SOURCE: Maps user values (0-100) to the source range [min_value, max_value].
    0 always maps to 0; values 1-100 are mapped linearly to min_value..max_value.
  - RemapDirection.FROM_SOURCE: Maps source values [min_value, max_value] to the user scale (0-100).
    0 always maps to 0; min_value..max_value are mapped linearly to 1-100.

  Always returns a rounded integer to avoid off-by-one errors.
  Output is clamped to [min_value, max_value] for TO_SOURCE and [0, 100] for FROM_SOURCE.
  """
  if value is None:
    return None
  if value == 0:
    return 0
  if max_value == min_value:
    return 0
  if direction == RemapDirection.TO_SOURCE:
    # 1..100 maps to min_value..max_value linearly
    result = int(round((value - 1) * (max_value - min_value) / 99 + min_value))
    return max(min(result, max_value), min_value)
  else:
    # min_value..max_value maps to 1..100 linearly
    result = int(round((value - min_value) * 99 / (max_value - min_value) + 1))
    return max(0, min(result, 100))

class MappedCover(CoverEntity):
  def __init__(self, hass, entry: ConfigEntry, cover, throttler: Throttler):
    self.hass = hass
    self._throttler = throttler
    self._entry = entry
    self._source_entity_id = cover
    self._target_position = None
    self._target_tilt = None
    self._target_changed_event = asyncio.Event()
    self._last_position_command = 0  # Timestamp of last position command
    ent_reg = entity_registry.async_get(self.hass)
    dev_reg = device_registry.async_get(self.hass)
    cover = ent_reg.async_get(self._source_entity_id)
    self._device = dev_reg.async_get(cover.device_id)
    _LOGGER.debug("[%s] Created mapped cover entity", self._source_entity_id)

  @property
  def _source_current_position(self):
    src = self.hass.states.get(self._source_entity_id)
    if src and src.state not in ("unavailable", "unknown"):
      return src.attributes.get("current_position")
    return None

  @property
  def _source_current_tilt_position(self):
    src = self.hass.states.get(self._source_entity_id)
    if src and src.state not in ("unavailable", "unknown"):
      return src.attributes.get("current_tilt_position")
    return None

  @property
  def _rename_pattern(self):
    return self._entry.data.get("rename_pattern", const.DEFAULT_RENAME_PATTERN)
  @property
  def _rename_replacement(self):
    return self._entry.data.get("rename_replacement", const.DEFAULT_RENAME_REPLACEMENT)
  @property
  def _min_pos(self):
    return int(self._entry.data.get("min_position", const.DEFAULT_MIN_POSITION))
  @property
  def _max_pos(self):
    return int(self._entry.data.get("max_position", const.DEFAULT_MAX_POSITION))
  @property
  def _min_tilt(self):
    return int(self._entry.data.get("min_tilt_position", const.DEFAULT_MIN_TILT_POSITION))
  @property
  def _max_tilt(self):
    return int(self._entry.data.get("max_tilt_position", const.DEFAULT_MAX_TILT_POSITION))
  @property
  def _close_tilt_if_down(self):
    return bool(self._entry.data.get("close_tilt_if_down", const.DEFAULT_CLOSE_TILT_IF_DOWN))

  @property
  def name(self):
    return re.sub(self._rename_pattern, self._rename_replacement, self._device and self._device.name or self._source_entity_id, count=1)

  @property
  def device_info(self):
    # Provide device info so the entity is grouped under the integration
    return {
      "identifiers": {(const.DOMAIN, self.unique_id)},
      "name": self.name,
      "manufacturer": "Mapped Cover Integration",
      "model": "Virtual Cover",
    }

  @property
  def unique_id(self):
    return f"{self._entry.entry_id}_{self._source_entity_id}"

  @property
  def supported_features(self):
    src = self.hass.states.get(self._source_entity_id)
    if not src:
      _LOGGER.debug("[%s] Source entity not found for supported_features", self._source_entity_id)
      return 0
    features = src.attributes.get("supported_features", 0)
    # Only expose features that are remapped
    feature_mask = (
      CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION | CoverEntityFeature.STOP |
      CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT | CoverEntityFeature.SET_TILT_POSITION | CoverEntityFeature.STOP_TILT
    )
    return features & feature_mask

  @property
  def is_closed(self):
    return self.current_cover_position == 0 and self.current_cover_tilt_position in (0, None)

  @property
  def is_closing(self):
    pos = self._source_current_position
    if self._target_position is not None and self._source_current_position is not None:
      return self._target_position < pos
    return super().is_closing

  @property
  def is_opening(self):
    pos = self._source_current_position
    if self._target_position is not None and self._source_current_position is not None:
      return self._target_position > pos
    return super().is_opening

  @property
  def current_cover_position(self):
    if self._target_position is not None:
      return remap_value(
        self._target_position,
        min_value=self._min_pos, max_value=self._max_pos,
        direction=RemapDirection.FROM_SOURCE
      )
    pos = self._source_current_position
    if pos is not None:
      return remap_value(
        pos,
        min_value=self._min_pos, max_value=self._max_pos,
        direction=RemapDirection.FROM_SOURCE
      )
    return None

  @property
  def current_cover_tilt_position(self):
    tilt = self._target_tilt
    if tilt is None:
      tilt = self._source_current_tilt_position
    if tilt is not None:
      tilt = remap_value(
        tilt,
        min_value=self._min_tilt, max_value=self._max_tilt,
        direction=RemapDirection.FROM_SOURCE
      )

    return tilt

  @property
  def available(self):
    src = self.hass.states.get(self._source_entity_id)
    return src is not None and src.state not in ("unavailable", "unknown")

  @property
  def device_class(self):
    """Reflect the device_class ("Shown As") of the underlying cover by default."""
    src = self.hass.states.get(self._source_entity_id)
    if src is not None:
      return src.attributes.get("device_class")
    return None

  @property
  def is_moving(self):
    # Consider moving if a position command was sent in the last 5 seconds
    recently_moving = (time.time() - self._last_position_command) < 5
    src = self.hass.states.get(self._source_entity_id)
    state = src.state if src else None
    return recently_moving or (state in (CoverState.OPENING, CoverState.CLOSING))

  async def _wait_for_attribute(self, attr, src_target, timeout=30, compare=lambda val, target: abs(val - target) <= 1):
    """Wait until the underlying cover's attribute matches the src_target (source scale), or until the target changes. Returns True if reached, False if timeout or interrupted."""
    def _attr_reached(state):
      if state is None or state.state in ("unavailable", "unknown"):
        return False
      val = state.attributes.get(attr)
      if val is None:
        return False
      return compare(val, src_target)
    hass = self.hass
    entity_id = self._source_entity_id
    fut = hass.loop.create_future()
    event = self._target_changed_event
    event.clear()

    @callback
    def state_listener(event_):
      new_state = event_.data.get("new_state")
      if _attr_reached(new_state):
        if not fut.done():
          fut.set_result(True)

    remove = async_track_state_change_event(hass, [entity_id], state_listener)
    # Check current state immediately
    state = hass.states.get(entity_id)
    if _attr_reached(state):
      remove()
      return True
    try:
      event_wait_task = asyncio.create_task(event.wait())
      done, _ = await asyncio.wait(
        [fut, event_wait_task],
        timeout=timeout,
        return_when=asyncio.FIRST_COMPLETED,
      )
      if fut in done and fut.done() and fut.result():
        return True
      return False
    finally:
      remove()

  async def _call_service(self, command, data, retry=0, timeout=30):
    """
    Asynchronously call a Home Assistant cover service with optional retries and attribute confirmation.
    Args:
      command (str): The cover service command to call. Must be one of:
        "set_cover_position", "set_cover_tilt_position", "stop_cover", or "stop_cover_tilt".
      data (dict): The service data to send with the command.
      retry (int, optional): Number of times to retry the command if the target attribute is not reached. Defaults to 0 (no retry).
      timeout (int, optional): Timeout in seconds to wait for the attribute to reach the target value after calling the service. Defaults to 30.
    Returns:
      bool: True if the service call succeeded (and the attribute reached the target value if applicable), False otherwise.
    Raises:
      ValueError: If the command is not in the allowed set.
    """

    allowed_commands = {
      "set_cover_position",
      "set_cover_tilt_position",
      "stop_cover",
      "stop_cover_tilt",
    }
    if command not in allowed_commands:
      raise ValueError(f"Command {command} not allowed")
    attempt = 0
    while True:
      try:
        async with self._throttler:
          await self.hass.services.async_call(
            "cover", command, data, blocking=True
          )
        # For set_cover_position and set_cover_tilt_position, wait for attribute to reach target
        if retry > 0 and command == "set_cover_position" and "position" in data:
          reached = await self._wait_for_attribute("current_position", data["position"], timeout=timeout)
          if reached:
            return True
          else:
            _LOGGER.debug("[%s] _call_service: %s did not reach position %s (attempt %d)", self._source_entity_id, command, data["position"], attempt + 1)
        elif retry > 0 and command == "set_cover_tilt_position" and "tilt_position" in data:
          reached = await self._wait_for_attribute("current_tilt_position", data["tilt_position"], timeout=timeout)
          if reached:
            return True
          else:
            _LOGGER.debug("[%s] _call_service: %s did not reach tilt %s (attempt %d)", self._source_entity_id, command, data["tilt_position"], attempt + 1)
        else:
          return True
      except Exception as e:
        _LOGGER.warning("[%s] _call_service: Exception on %s: %s (attempt %d)", self._source_entity_id, command, e, attempt + 1)
      attempt += 1
      if attempt > retry and retry > 0:
        _LOGGER.warning("[%s] _call_service: Max retries (%s) reached for %s", self._source_entity_id, retry, command)
        break
      await asyncio.sleep(1)
    return False

  async def converge_position(self):
    """
    Try to converge the underlying cover to the current target position and/or tilt.
    If both are set, set tilt first if position needs to move (target != current and not recently moving), otherwise set position first then tilt.
    Resets self._target_position and self._target_tilt after move, but only after confirming the underlying state.
    If targets change during execution, exit early; a new converge will be scheduled.
    Now: raise the changed event here instead of in the setters.
    """
    # Raise the event immediately to interrupt any other waits
    self._target_changed_event.set()
    position = self._target_position
    tilt = self._target_tilt
    current_pos = self._source_current_position
    _LOGGER.debug("[%s] converge_position: target_position=%s, target_tilt=%s, current_pos=%s", self._source_entity_id, position, tilt, current_pos)
    # Set tilt first if both are set and (target position != current) and the cover is not recently moving
    if tilt is not None and position is not None and (current_pos is None or position != current_pos) and not self.is_moving:
      _LOGGER.debug(
        "[%s] Setting tilt before position: tilt_position=%s (target_position=%s)",
        self._source_entity_id, tilt, position
      )
      await self._call_service(
        "set_cover_tilt_position",
        {"entity_id": self._source_entity_id, "tilt_position": tilt},
      )
      if self._target_position != position or self._target_tilt != tilt:
        _LOGGER.debug("[%s] converge_position: abort (position=%s, tilt=%s)", self._source_entity_id, position, tilt)
        return

    current_pos = self._source_current_position

    # If the cover is moving and the target position is equal to the current position,
    # stop the cover and look for its current position again
    if self.is_moving and current_pos == position:
      _LOGGER.debug("[%s] Cover is moving but already at target position, stopping", self._source_entity_id)
      await asyncio.sleep(1)
      await self._call_service("stop_cover", {"entity_id": self._source_entity_id})
      await self._wait_for_attribute("current_position", current_pos, timeout=5, compare=lambda val, target: abs(val - target) > 1)
      current_pos = self._source_current_position
      self.async_write_ha_state()

    # Set position if needed
    if position is not None and current_pos != position:
      await self._call_service(
        "set_cover_position",
        {"entity_id": self._source_entity_id, "position": position},
        retry=3
      )
      self.async_write_ha_state()

    # Set tilt if needed
    if tilt is not None:
      current_tilt = self._source_current_tilt_position

      # Set tilt to 0 before setting the target tilt if close_tilt_if_down is enabled and
      # target position is below current position
      if self._close_tilt_if_down and position is None and tilt < current_tilt:
        await self._call_service(
          "set_cover_tilt_position",
          {"entity_id": self._source_entity_id, "tilt_position": 0},
          retry=3
        )

      reached = False

      if position is not None and current_pos != position:
        reached = await self._wait_for_attribute("current_tilt_position", tilt, 5)

      if self._target_position != position or self._target_tilt != tilt:
        _LOGGER.debug("[%s] converge_position: abort (position=%s, tilt=%s)", self._source_entity_id, position, tilt)
        return

      if not reached:
        await self._call_service(
          "set_cover_tilt_position",
          {"entity_id": self._source_entity_id, "tilt_position": tilt},
          retry=3
        )

    self._target_position = None
    self._target_tilt = None
    self.async_write_ha_state()
    _LOGGER.debug("[%s] converge_position: DONE", self._source_entity_id)

  async def async_set_cover_position(self, **kwargs):
    position = kwargs.get("position")
    if position is None:
      _LOGGER.debug("[%s] async_set_cover_position: No position provided", self._source_entity_id)
      return
    new_target = remap_value(position, self._min_pos, self._max_pos, direction=RemapDirection.TO_SOURCE)
    # Only call converge_position if the target is different from the current target or current position
    if self._target_position == new_target:
      _LOGGER.debug("[%s] async_set_cover_position: Target already set to %s", self._source_entity_id, new_target)
      return
    src = self.hass.states.get(self._source_entity_id)
    current_pos = self._source_current_position
    if self._target_position is None and current_pos == new_target:
      _LOGGER.debug("[%s] async_set_cover_position: Already at target position %s", self._source_entity_id, new_target)
      return
    self._target_position = new_target
    # Set current tilt as target tilt if target tilt is None
    if self._target_tilt is None:
      current_tilt = self._source_current_tilt_position
      if current_tilt is not None:
        self._target_tilt = current_tilt
    self.hass.async_create_task(self.converge_position())

  async def async_set_cover_tilt_position(self, **kwargs):
    tilt = kwargs.get("tilt_position")
    if tilt is None:
      _LOGGER.debug("[%s] async_set_cover_tilt_position: No tilt_position provided", self._source_entity_id)
      return
    new_target = remap_value(tilt, self._min_tilt, self._max_tilt, direction=RemapDirection.TO_SOURCE)
    if self._target_tilt == new_target:
      _LOGGER.debug("[%s] async_set_cover_tilt_position: Target already set to %s", self._source_entity_id, new_target)
      return
    src = self.hass.states.get(self._source_entity_id)
    current_tilt = self._source_current_tilt_position
    if self._target_tilt is None and current_tilt == new_target:
      _LOGGER.debug("[%s] async_set_cover_tilt_position: Already at target tilt %s", self._source_entity_id, new_target)
      return
    self._target_tilt = new_target
    self.hass.async_create_task(self.converge_position())

  async def async_open_cover(self, **kwargs):
    features = self.supported_features

    if self._source_current_position != self._max_pos:
      self._target_position = self._max_pos
    if features & CoverEntityFeature.SET_TILT_POSITION and self._source_current_tilt_position != self._max_tilt:
      self._target_tilt = self._max_tilt
    if self._target_position is not None or self._target_tilt is not None:
      self.hass.async_create_task(self.converge_position())

  async def async_close_cover(self, **kwargs):
    features = self.supported_features
    if self._source_current_position != 0:
      self._target_position = 0
    if features & CoverEntityFeature.SET_TILT_POSITION and self._source_current_tilt_position != 0:
      self._target_tilt = 0
    if self._target_position is not None or self._target_tilt is not None:
      self.hass.async_create_task(self.converge_position())

  async def async_open_cover_tilt(self, **kwargs):
    if self._source_current_tilt_position != self._max_tilt:
      self._target_tilt = self._max_tilt
      self.hass.async_create_task(self.converge_position())

  async def async_close_cover_tilt(self, **kwargs):
    if self._source_current_tilt_position != 0:
      self._target_tilt = 0
      self.hass.async_create_task(self.converge_position())

  async def async_stop_cover(self, **kwargs):
    _LOGGER.debug(
      "[%s] Calling stop_cover",
      self._source_entity_id
    )
    self._target_position = None
    self._target_tilt = None
    self._target_changed_event.set()
    await self._call_service(
      "stop_cover",
      {"entity_id": self._source_entity_id},
      retry=3
    )
    self.async_write_ha_state()

  async def async_stop_cover_tilt(self, **kwargs):
    _LOGGER.debug(
      "[%s] Calling stop_cover_tilt",
      self._source_entity_id
    )
    self._target_tilt = None
    self._target_changed_event.set()
    await self._call_service(
      "stop_cover_tilt",
      {"entity_id": self._source_entity_id},
      retry=3
    )
    self.async_write_ha_state()
