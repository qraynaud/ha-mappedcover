"""
Cover platform for mappedcover integration.
"""
import logging
from enum import Enum
import asyncio
from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.core import callback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the mapped cover cover from a config entry."""
    async_add_entities([
        MappedCover(hass, entry)
    ])

class RemapDirection(Enum):
    TO_SOURCE = 1
    FROM_SOURCE = 2

def remap_value(value, min_user, max_user, direction=RemapDirection.TO_SOURCE):
    """
    Remap value between user and source scale.
    - RemapDirection.TO_SOURCE: user (0-100, 0 always maps to 0, 1-100 to min..max)
    - RemapDirection.FROM_SOURCE: source (0-100, 0 always maps to 0, min..max to 1-100)
    """
    if value is None:
        return None
    if value == 0:
        return 0
    if max_user == min_user:
        return 0
    if direction == RemapDirection.TO_SOURCE:
        # 1..100 maps to min..max linearly
        return int(round((value - 1) * (max_user - min_user) / 99 + min_user))
    else:
        # min..max maps to 1..100 linearly
        return int(round((value - min_user) * 99 / (max_user - min_user) + 1))

async def async_wait_for_state(hass, entity_id, check, timeout=60):
    """
    Wait until the entity_id's state matches the check function or is in the given state list.
    check: either a callable(state) -> bool or a list of state strings.
    Returns when the condition is met or raises asyncio.TimeoutError.
    """
    import asyncio
    fut = hass.loop.create_future()

    if isinstance(check, list):
        def _check(state):
            return state is not None and state.state in check
    else:
        _check = check

    @callback
    def state_listener(event):
        new_state = event.data.get("new_state")
        if _check(new_state):
            if not fut.done():
                fut.set_result(True)

    remove = async_track_state_change_event(hass, [entity_id], state_listener)
    # Check current state immediately
    state = hass.states.get(entity_id)
    if _check(state):
        remove()
        return
    try:
        await asyncio.wait_for(fut, timeout)
    finally:
        remove()

class MappedCover(CoverEntity):
    def __init__(self, hass, entry):
        self.hass = hass
        self._entry = entry
        self._config = entry.options or entry.data
        self._name = self._config.get("cover_name")
        self._source_entity_id = self._config.get("cover_entity")
        self._min_pos = int(self._config.get("min_position", 0))
        self._max_pos = int(self._config.get("max_position", 100))
        self._min_tilt = int(self._config.get("min_tilt_position", 0))
        self._max_tilt = int(self._config.get("max_tilt_position", 100))
        self._target_position = None
        self._target_tilt = None
        self._converge_lock = asyncio.Lock()
        self._target_changed_event = asyncio.Event()

    @property
    def name(self):
        return self._name

    @property
    def device_info(self):
        # Provide device info so the entity is grouped under the integration
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self._name,
            "manufacturer": "Mapped Cover Integration",
            "model": "Virtual Mapped Cover",
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
                self._min_pos, self._max_pos,
                direction=RemapDirection.FROM_SOURCE
            )
        src = self.hass.states.get(self._source_entity_id)
        if src and src.state not in ("unavailable", "unknown"):
            pos = src.attributes.get("current_position")
            if pos is not None:
                return remap_value(
                    pos,
                    self._min_pos, self._max_pos,
                    direction=RemapDirection.FROM_SOURCE
                )
        return None

    @property
    def current_cover_tilt_position(self):
        if self._target_tilt is not None:
            return remap_value(
                self._target_tilt,
                self._min_tilt, self._max_tilt,
                direction=RemapDirection.FROM_SOURCE
            )
        src = self.hass.states.get(self._source_entity_id)
        if src and src.state not in ("unavailable", "unknown"):
            tilt = src.attributes.get("current_tilt_position")
            if tilt is not None:
                return remap_value(
                    tilt,
                    self._min_tilt, self._max_tilt,
                    direction=RemapDirection.FROM_SOURCE
                )
        return None

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

    async def _wait_for_attribute(self, attr, src_target, timeout=10):
        """Wait until the underlying cover's attribute matches the src_target (source scale), or until the target changes. Returns True if reached, False if timeout or interrupted."""
        def _attr_reached(state):
            if state is None or state.state in ("unavailable", "unknown"):
                return False
            val = state.attributes.get(attr)
            if val is None:
                return False
            return abs(val - src_target) <= 1
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

    async def converge_position(self, timeout=10):
        """
        Try to converge the underlying cover to the current target position and/or tilt.
        If both are set, set tilt first if position needs to move (target != current or is_moving), otherwise set position first then tilt.
        Resets self._target_position and self._target_tilt after move, but only after confirming the underlying state.
        If targets change during execution, exit early; a new converge will be scheduled.
        Now: raise the changed event here instead of in the setters.
        """
        # Raise the event immediately to interrupt any other waits
        self._target_changed_event.set()
        # Then clear it for this run
        self._target_changed_event.clear()
        position = self._target_position
        tilt = self._target_tilt
        src = self.hass.states.get(self._source_entity_id)
        current_pos = src.attributes.get("current_position") if src else None
        is_moving = src and src.state in ("opening", "closing")

        # Set tilt first if both are set and (target position != current or is_moving)
        if tilt is not None and position is not None and (current_pos is None or position != current_pos or is_moving):
            await self.hass.services.async_call(
                "cover", "set_cover_tilt_position",
                {"entity_id": self._source_entity_id, "tilt_position": tilt},
                blocking=True
            )
            if self._target_position != position or self._target_tilt != tilt:
                return

        # Main convergence loop: keep trying until both targets are reached or changed
        while not (self._target_position is None and self._target_tilt is None):
            position = self._target_position
            tilt = self._target_tilt
            src = self.hass.states.get(self._source_entity_id)
            current_pos = src.attributes.get("current_position") if src else None
            is_moving = src and src.state in ("opening", "closing")

            # Set position if needed
            if position is not None:
                await self.hass.services.async_call(
                    "cover", "set_cover_position",
                    {"entity_id": self._source_entity_id, "position": position},
                    blocking=True
                )
                reached = await self._wait_for_attribute("current_position", position, timeout)
                if self._target_position != position or self._target_tilt != tilt:
                    return
                if reached:
                    self._target_position = None
                if tilt is not None:
                    src = self.hass.states.get(self._source_entity_id)
                    is_moving = src and src.state in ("opening", "closing")
                    if is_moving:
                        await async_wait_for_state(
                            self.hass,
                            self._source_entity_id,
                            state=["open", "closed", "unknown", "unavailable"],
                            timeout=timeout,
                        )
                    if self._target_position != position or self._target_tilt != tilt:
                        return

            # Set tilt if needed (and not already set above)
            if tilt is not None and (position is None or current_pos == position):
                await self.hass.services.async_call(
                    "cover", "set_cover_tilt_position",
                    {"entity_id": self._source_entity_id, "tilt_position": tilt},
                    blocking=True
                )
                reached = await self._wait_for_attribute("current_tilt_position", tilt, timeout)
                if self._target_position != position or self._target_tilt != tilt:
                    return
                if reached:
                    self._target_tilt = None

        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs):
        position = kwargs.get("position")
        if position is None:
            return
        self._target_position = remap_value(position, self._min_pos, self._max_pos, direction=RemapDirection.TO_SOURCE)
        self.hass.async_create_task(self.converge_position())
        self.async_write_ha_state()
        return True

    async def async_set_cover_tilt_position(self, **kwargs):
        tilt = kwargs.get("tilt_position")
        if tilt is None:
            return
        self._target_tilt = remap_value(tilt, self._min_tilt, self._max_tilt, direction=RemapDirection.TO_SOURCE)
        self.hass.async_create_task(self.converge_position())
        self.async_write_ha_state()
        return True

    async def async_open_cover(self, **kwargs):
        features = self.supported_features
        self._target_position = self._max_pos
        if features & CoverEntityFeature.SET_TILT_POSITION:
            self._target_tilt = self._max_tilt
        self.hass.async_create_task(self.converge_position())
        self.async_write_ha_state()
        return True

    async def async_close_cover(self, **kwargs):
        features = self.supported_features
        self._target_position = 0
        if features & CoverEntityFeature.SET_TILT_POSITION:
            self._target_tilt = 0
        self.hass.async_create_task(self.converge_position())
        self.async_write_ha_state()
        return True

    async def async_open_cover_tilt(self, **kwargs):
        await self.hass.services.async_call(
            "cover", "open_cover_tilt", {"entity_id": self._source_entity_id}, blocking=True
        )
        self._target_tilt = self._max_tilt
        self.async_write_ha_state()
        return True

    async def async_close_cover_tilt(self, **kwargs):
        await self.hass.services.async_call(
            "cover", "close_cover_tilt", {"entity_id": self._source_entity_id}, blocking=True
        )
        self._target_tilt = self._min_tilt
        self.async_write_ha_state()
        return True

    async def async_stop_cover(self, **kwargs):
        await self.hass.services.async_call(
            "cover", "stop_cover", {"entity_id": self._source_entity_id}, blocking=True
        )
        self._target_position = None
        self._target_tilt = None
        self._target_changed_event.set()
        self.async_write_ha_state()

    async def async_stop_cover_tilt(self, **kwargs):
        await self.hass.services.async_call(
            "cover", "stop_cover_tilt", {"entity_id": self._source_entity_id}, blocking=True
        )
        self._target_position = None
        self._target_tilt = None
        self._target_changed_event.set()
        self.async_write_ha_state()

    async def async_update(self):
        pass
