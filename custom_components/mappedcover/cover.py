"""
Cover platform for mappedcover integration.
"""
import logging
from enum import Enum
import asyncio
import time
from homeassistant.components.cover import (
  CoverEntity,
  CoverEntityFeature,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers import entity_registry
from homeassistant.helpers import device_registry
from homeassistant.core import callback
from .const import DOMAIN
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
  """Set up the mapped cover from a config entry."""
  covers = entry.data.get("covers", [])
  ent_reg = entity_registry.async_get(hass)
  dev_reg = device_registry.async_get(hass)

  # Remove outdated entities
  for entity in list(ent_reg.entities.values()):
    if (
      entity.platform == DOMAIN
      and entity.config_entry_id == entry.entry_id
      and entity.entity_id not in [f"cover.{cover}" for cover in covers]
    ):
      ent_reg.async_remove(entity.entity_id)
      dev_reg.async_remove_device(entity.device_id)

  mapped_entities = []
  for cover in covers:
    mapped_entities.append(MappedCover(hass, entry, cover))
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
  def __init__(self, hass, entry: ConfigEntry, cover):
    self.hass = hass
    self._entry = entry
    self._source_entity_id = cover
    self._target_position = None
    self._target_tilt = None
    self._target_changed_event = asyncio.Event()
    self._last_position_command = 0  # Timestamp of last position command
    _LOGGER.debug("[MappedCover] created: %s (close tilt: %s)", self._source_entity_id, self._close_tilt_if_down)

  @property
  def _min_pos(self):
    return int(self._entry.data.get("min_position", 0))
  @property
  def _max_pos(self):
    return int(self._entry.data.get("max_position", 0))
  @property
  def _min_tilt(self):
    return int(self._entry.data.get("min_tilt_position", 0))
  @property
  def _max_tilt(self):
    return int(self._entry.data.get("max_tilt_position", 0))
  @property
  def _close_tilt_if_down(self):
    return bool(self._entry.data.get("close_tilt_if_down", True))

  @property
  def name(self):
    ent_reg = entity_registry.async_get(self.hass)
    dev_reg = device_registry.async_get(self.hass)
    cover = ent_reg.async_get(self._source_entity_id)
    device = dev_reg.async_get(cover.device_id)
    return f"Mapped {device and device.name or self._source_entity_id}"

  @property
  def device_info(self):
    # Provide device info so the entity is grouped under the integration
    return {
      "identifiers": {(DOMAIN, self.unique_id)},
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
    return self.current_cover_position == 0

  @property
  def current_cover_position(self):
    if self._target_position is not None:
      return remap_value(
        self._target_position,
        min_value=self._min_pos, max_value=self._max_pos,
        direction=RemapDirection.FROM_SOURCE
      )
    src = self.hass.states.get(self._source_entity_id)
    if src and src.state not in ("unavailable", "unknown"):
      pos = src.attributes.get("current_position")
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
      src = self.hass.states.get(self._source_entity_id)
      tilt = src.attributes.get("current_tilt_position")

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
    return src is not None and src.state != "unavailable"

  @property
  def state(self):
    src = self.hass.states.get(self._source_entity_id)
    # If underlying state is 'closed' but tilt is not 0, return 'open'
    if src and src.state == "closed":
      tilt = src.attributes.get("current_tilt_position")
      if tilt is not None and (tilt != 0 or self._target_tilt is not None):
        return "open"
      return "closed"
    if self._target_position is not None and src and src.state not in ("unavailable", "unknown"):
      pos = src.attributes.get("current_position")
      if pos is not None:
        if self._target_position > pos:
          return "opening"
        elif self._target_position < pos:
          return "closing"
    if src:
      return src.state
    return None

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
    return recently_moving or (state in ("opening", "closing"))

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

  async def _set_position_and_wait(self, position, timeout=30):
    self._last_position_command = time.time()
    _LOGGER.debug(
      "[MappedCover] Calling set_cover_position: entity_id=%s, position=%s",
      self._source_entity_id, position
    )
    await self.hass.services.async_call(
      "cover", "set_cover_position",
      {"entity_id": self._source_entity_id, "position": position},
      blocking=True
    )
    _LOGGER.debug(
      "[MappedCover] Waiting for position to be reached after set_cover_position: entity_id=%s, position=%s",
      self._source_entity_id, position
    )
    reached = await self._wait_for_attribute("current_position", position, timeout=timeout)
    if reached:
      self._last_position_command = 0
    return reached

  async def _set_tilt_position_and_wait(self, tilt, timeout=5):
    _LOGGER.debug(
      "[MappedCover] Calling set_cover_tilt_position: entity_id=%s, tilt_position=%s",
      self._source_entity_id, tilt
    )
    await self.hass.services.async_call(
      "cover", "set_cover_tilt_position",
      {"entity_id": self._source_entity_id, "tilt_position": tilt},
      blocking=True
    )
    _LOGGER.debug(
      "[MappedCover] Waiting for tilt to be reached after set_cover_tilt_position: entity_id=%s", self._source_entity_id
    )
    return await self._wait_for_attribute("current_tilt_position", tilt, timeout)

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
    src = self.hass.states.get(self._source_entity_id)
    current_pos = src.attributes.get("current_position") if src else None

    # Set tilt first if both are set and (target position != current) and the cover is not recently moving
    if tilt is not None and position is not None and (current_pos is None or position != current_pos) and not self.is_moving:
      _LOGGER.debug(
        "[MappedCover] Calling set_cover_tilt_position: entity_id=%s, tilt_position=%s (target_position=%s)",
        self._source_entity_id, tilt, position
      )
      await self.hass.services.async_call(
        "cover", "set_cover_tilt_position",
        {"entity_id": self._source_entity_id, "tilt_position": tilt},
        blocking=True
      )
      if self._target_position != position or self._target_tilt != tilt:
        _LOGGER.debug("[MappedCover] Abort (position=%s, tilt=%s)!", position, tilt)
        return

    src = self.hass.states.get(self._source_entity_id)
    current_pos = src.attributes.get("current_position") if src else None

    # If the cover is moving and the target position is equal to the current position,
    # stop the cover and look for its current position again
    if self.is_moving and current_pos == position:
      await asyncio.sleep(1)
      await self.hass.services.async_call(
        "cover", "stop_cover", {"entity_id": self._source_entity_id}, blocking=True
      )
      await self._wait_for_attribute("current_position", current_pos, timeout=5, compare=lambda val, target: abs(val - target) > 1)
      src = self.hass.states.get(self._source_entity_id)
      current_pos = src.attributes.get("current_position") if src else None

    # Set position if needed
    if position is not None and current_pos != position:
      index = 0
      while index < 10:
        index += 1
        reached = await self._set_position_and_wait(position)
        if self._target_position != position or self._target_tilt != tilt:
          _LOGGER.debug("[MappedCover] Abort (position=%s, tilt=%s)!", position, tilt)
          return
        if reached:
          break
      if index == 10:
        _LOGGER.debug(
          "[MappedCover] Failed to reach position after 10 tries: entity_id=%s, position=%s",
          self._source_entity_id, position
        )

    self.async_write_ha_state()

    # Set tilt if needed
    if tilt is not None:
      src = self.hass.states.get(self._source_entity_id)
      current_tilt = src.attributes.get("current_tilt_position") if src else None

      # Set tilt to 0 before setting the target tilt if close_tilt_if_down is enabled and
      # target position is below current position
      if self._close_tilt_if_down and position is None and tilt < current_tilt:
        while not await self._set_tilt_position_and_wait(0):
          pass

      reached = False
      index = 0

      if position is not None and current_pos != position:
        reached = await self._wait_for_attribute("current_tilt_position", tilt, 5)

      if self._target_position != position or self._target_tilt != tilt:
          _LOGGER.debug("[MappedCover] Abort (position=%s, tilt=%s)!", position, tilt)
          return

      while not reached and index < 10:
        index += 1
        reached = await self._set_tilt_position_and_wait(tilt)
        if self._target_position != position or self._target_tilt != tilt:
          _LOGGER.debug("[MappedCover] Abort (position=%s, tilt=%s)!", position, tilt)
          return

      if index == 10:
        _LOGGER.debug(
          "[MappedCover] Failed to reach tilt after 10 tries: entity_id=%s, tilt_position=%s",
          self._source_entity_id, tilt
        )

    self._target_position = None
    self._target_tilt = None
    self.async_write_ha_state()
    _LOGGER.debug("[MappedCover] DONE!")

  async def async_set_cover_position(self, **kwargs):
    position = kwargs.get("position")
    if position is None:
      return
    new_target = remap_value(position, self._min_pos, self._max_pos, direction=RemapDirection.TO_SOURCE)
    # Only call converge_position if the target is different from the current target or current position
    if self._target_position == new_target:
      return
    src = self.hass.states.get(self._source_entity_id)
    current_pos = src.attributes.get("current_position") if src else None
    if self._target_position is None and current_pos == new_target:
      return
    self._target_position = new_target
    # Set current tilt as target tilt if target tilt is None
    if self._target_tilt is None:
      current_tilt = src.attributes.get("current_tilt_position") if src else None
      if current_tilt is not None:
        self._target_tilt = current_tilt
    self.hass.async_create_task(self.converge_position())
    self.async_write_ha_state()

  async def async_set_cover_tilt_position(self, **kwargs):
    tilt = kwargs.get("tilt_position")
    if tilt is None:
      return
    new_target = remap_value(tilt, self._min_tilt, self._max_tilt, direction=RemapDirection.TO_SOURCE)
    if self._target_tilt == new_target:
      return
    src = self.hass.states.get(self._source_entity_id)
    current_tilt = src.attributes.get("current_tilt_position") if src else None
    if self._target_tilt is None and current_tilt == new_target:
      return
    self._target_tilt = new_target
    self.hass.async_create_task(self.converge_position())
    self.async_write_ha_state()

  async def async_open_cover(self, **kwargs):
    features = self.supported_features
    self._target_position = self._max_pos
    if features & CoverEntityFeature.SET_TILT_POSITION:
      self._target_tilt = self._max_tilt
    self.hass.async_create_task(self.converge_position())
    self.async_write_ha_state()

  async def async_close_cover(self, **kwargs):
    features = self.supported_features
    self._target_position = 0
    if features & CoverEntityFeature.SET_TILT_POSITION:
      self._target_tilt = 0
    self.hass.async_create_task(self.converge_position())
    self.async_write_ha_state()

  async def async_open_cover_tilt(self, **kwargs):
    _LOGGER.debug(
      "[MappedCover] Calling open_cover_tilt: entity_id=%s, tilt_position=%s",
      self._source_entity_id, self._max_tilt
    )
    await self.hass.services.async_call(
      "cover", "open_cover_tilt", {"entity_id": self._source_entity_id}, blocking=True
    )
    self._target_tilt = self._max_tilt
    self.async_write_ha_state()

  async def async_close_cover_tilt(self, **kwargs):
    _LOGGER.debug(
      "[MappedCover] Calling close_cover_tilt: entity_id=%s, tilt_position=%s",
      self._source_entity_id, self._min_tilt
    )
    await self.hass.services.async_call(
      "cover", "close_cover_tilt", {"entity_id": self._source_entity_id}, blocking=True
    )
    self._target_tilt = self._min_tilt
    self.async_write_ha_state()

  async def async_stop_cover(self, **kwargs):
    _LOGGER.debug(
      "[MappedCover] Calling stop_cover: entity_id=%s",
      self._source_entity_id
    )
    await self.hass.services.async_call(
      "cover", "stop_cover", {"entity_id": self._source_entity_id}, blocking=True
    )
    self._target_position = None
    self._target_tilt = None
    self._target_changed_event.set()
    self.async_write_ha_state()

  async def async_stop_cover_tilt(self, **kwargs):
    _LOGGER.debug(
      "[MappedCover] Calling stop_cover_tilt: entity_id=%s",
      self._source_entity_id
    )
    await self.hass.services.async_call(
      "cover", "stop_cover_tilt", {"entity_id": self._source_entity_id}, blocking=True
    )
    self._target_tilt = None
    self._target_changed_event.set()
    self.async_write_ha_state()
