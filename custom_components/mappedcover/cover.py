"""
Cover platform for mappedcover integration.

This module implements a virtual cover entity that maps position and tilt values
from source covers to different ranges, enabling unified control of covers with
varying position scales. The MappedCover entity acts as a proxy that translates
between user-defined ranges (0-100) and the source cover's actual range.
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

# Constants for operation timeouts and thresholds
# Consider cover recently moving within this time
RECENT_MOVEMENT_THRESHOLD_SECONDS = 5
# Default timeout for waiting on attribute changes
DEFAULT_OPERATION_TIMEOUT_SECONDS = 30
POSITION_TOLERANCE = 1  # Acceptable position difference for comparison
DEFAULT_RETRY_COUNT = 3  # Default number of retries for service calls


async def async_setup_entry(hass, entry, async_add_entities):
    """
    Set up the mapped cover entities from a config entry.

    This function creates MappedCover entities for each source cover specified
    in the config entry. It also handles cleanup of outdated entities and
    assigns appropriate device areas based on the source covers.

    Args:
      hass: Home Assistant instance
      entry: ConfigEntry containing the integration configuration
      async_add_entities: Callback to add new entities to Home Assistant
    """
    covers = entry.data.get("covers", [])
    throttle = entry.data.get("throttle", const.DEFAULT_THROTTLE)
    # Create throttler to prevent overwhelming the source covers with rapid commands
    throttler = Throttler(1, throttle / 1000)  # Convert ms to seconds
    ent_reg = entity_registry.async_get(hass)
    dev_reg = device_registry.async_get(hass)

    # Remove outdated entities that are no longer in the configuration
    # This prevents orphaned entities when the user changes the cover selection
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
    await async_add_entities(mapped_entities)

    # Set area assignments after entities are created to match source cover locations
    # This groups mapped covers with their physical counterparts in the UI
    for mapped_entity in mapped_entities:
        src_entity = ent_reg.async_get(mapped_entity._source_entity_id)
        src_device = dev_reg.async_get(
            src_entity.device_id) if src_entity and src_entity.device_id else None
        area_id = (src_device and src_device.area_id) or (
            src_entity and src_entity.area_id)
        if area_id:
            mapped_reg_entity = ent_reg.async_get(mapped_entity.entity_id)
            mapped_device = dev_reg.async_get(mapped_reg_entity.device_id)
            if mapped_device:
                dev_reg.async_update_device(mapped_device.id, area_id=area_id)


async def async_unload_entry(hass, entry):
    """
    Unload a config entry and clean up all associated entities.

    This function ensures proper cleanup of all mapped entities and their
    devices when the integration is unloaded or reconfigured.

    Args:
      hass: Home Assistant instance
      entry: ConfigEntry being unloaded

    Returns:
      bool: True if unload was successful
    """
    # Find and clean up mapped entities for this config entry
    _LOGGER.debug("Platform unloading entry: %s − covers: %s",
                  entry.entry_id, entry.data.get("covers", []))
    ent_reg = entity_registry.async_get(hass)
    dev_reg = device_registry.async_get(hass)

    # Find all mapped entities that belong to this config entry
    mapped_entities = [
        entity for entity in ent_reg.entities.values()
        if entity.platform == const.DOMAIN and entity.config_entry_id == entry.entry_id
    ]

    # Remove from registries - this triggers async_will_remove_from_hass for cleanup
    for entity_entry in mapped_entities:
        _LOGGER.debug("Removing mapped entity: %s", entity_entry.entity_id)
        ent_reg.async_remove(entity_entry.entity_id)
        if entity_entry.device_id:
            dev_reg.async_remove_device(entity_entry.device_id)

    return True


async def async_remove_entry(hass, entry):
    """
    Remove a config entry completely.

    This is called when the integration is being permanently removed.
    Currently delegates to async_unload_entry for cleanup.

    Args:
      hass: Home Assistant instance
      entry: ConfigEntry being removed

    Returns:
      bool: True if removal was successful
    """
    return async_unload_entry(hass, entry)


class RemapDirection(Enum):
    """
    Direction for value remapping between user scale (0-100) and source scale.

    TO_SOURCE: Convert from user scale (0-100) to source scale (min_value..max_value)
    FROM_SOURCE: Convert from source scale (min_value..max_value) to user scale (0-100)
    """
    TO_SOURCE = 1
    FROM_SOURCE = 2


def remap_value(value, min_value, max_value, direction=RemapDirection.TO_SOURCE):
    """
    Remap values between user scale (0-100) and source cover's actual range.

    This is the core mathematical function that enables position mapping. It handles
    the special case where 0 always maps to 0 (fully closed), while other values
    are mapped linearly within their respective ranges.

    Mathematical behavior:
    - TO_SOURCE: Maps user values (0-100) to source range [min_value, max_value]
      * 0 → 0 (always, represents fully closed)
      * 1-100 → min_value to max_value (linear mapping)
      * Formula: (value-1) * (max_value-min_value) / 99 + min_value

    - FROM_SOURCE: Maps source values [min_value, max_value] to user scale (0-100)
      * 0 → 0 (always, represents fully closed)
      * min_value to max_value → 1 to 100 (linear mapping)
      * Values below min_value are clamped to min_value (then mapped to 1)
      * Formula: (value-min_value) * 99 / (max_value-min_value) + 1

    Args:
      value (int|None): The value to remap. None values pass through unchanged.
      min_value (int): Minimum value of the source cover's range (when partially open).
      max_value (int): Maximum value of the source cover's range (when fully open).
      direction (RemapDirection): Direction of the mapping operation.

    Returns:
      int|None: Remapped value rounded to nearest integer, or None if input was None.
                  For TO_SOURCE: clamped to [min_value, max_value]
                  For FROM_SOURCE: clamped to [0, 100]

    Examples:
      >>> remap_value(50, 20, 80, RemapDirection.TO_SOURCE)
      50  # Maps 50% user scale to middle of 20-80 range
      >>> remap_value(50, 20, 80, RemapDirection.FROM_SOURCE)
      51  # Maps source value 50 to user scale percentage
    """
    if value is None:
        return None
    if value == 0:
        return 0  # 0 always represents fully closed in both directions
    if max_value == min_value:
        # Handle edge case where source range has no spread
        return 0 if direction == RemapDirection.TO_SOURCE else min_value

    if direction == RemapDirection.TO_SOURCE:
        # Map user scale 1-100 to source range min_value..max_value linearly
        result = int(
            round((value - 1) * (max_value - min_value) / 99 + min_value))
        return max(min(result, max_value), min_value)  # Clamp to valid range
    else:
        # Map source range to user scale 1-100
        if value < min_value:
            # Values below minimum are treated as minimum (slightly open)
            return 1
        # Linear mapping from source range to user scale 1-100
        result = int(round((value - min_value) * 99 /
                     (max_value - min_value) + 1))
        return max(1, min(result, 100))  # Clamp to valid percentage range


class MappedCover(CoverEntity):
    """
    A virtual cover entity that maps position/tilt values from a source cover to different ranges.

    This entity acts as a proxy for a source cover, translating between the user's desired
    position range (configured via min/max position settings) and the source cover's
    actual range (0-100). This enables unified control of covers that may have different
    position interpretations or physical constraints.

    Key Features:
    - Position remapping: Maps user scale (0-100) to source scale (min_pos..max_pos)
    - Tilt remapping: Maps user scale (0-100) to source scale (min_tilt..max_tilt)
    - Throttled commands: Prevents overwhelming source covers with rapid commands
    - Target tracking: Maintains desired position state separate from current position
    - Convergence logic: Handles complex movement scenarios (position + tilt coordination)
    - Proper cleanup: Manages async resources and prevents task leaks

    State Management:
    - _target_position: Desired position in source scale (None when not moving)
    - _target_tilt: Desired tilt in source scale (None when not moving)
    - _target_changed_event: Async event to coordinate movement operations
    - _running_tasks: Set of active async tasks for proper cleanup
    - _state_listeners: List of state change listeners for cleanup

    Args:
      hass: Home Assistant instance
      entry: ConfigEntry containing integration configuration
      cover: Entity ID of the source cover to proxy
      throttler: Throttler instance to rate-limit service calls
    """

    def __init__(self, hass, entry: ConfigEntry, cover, throttler: Throttler):
        """Initialize a MappedCover entity with proper resource tracking."""
        self.hass = hass
        self._throttler = throttler
        self._entry = entry
        self._source_entity_id = cover

        # Target state tracking - None means no active movement command
        self._target_position = None
        self._target_tilt = None
        self._target_changed_event = asyncio.Event()  # Coordinates movement operations

        # Movement detection - tracks when position commands were issued
        self._last_position_command = 0  # Timestamp of last position command

        # Resource management for proper cleanup
        self._running_tasks = set()  # Track running tasks for cleanup
        self._state_listeners = []  # Track state listeners for cleanup

        # Device and entity registry access for name resolution and area assignment
        ent_reg = entity_registry.async_get(self.hass)
        dev_reg = device_registry.async_get(self.hass)
        cover = ent_reg.async_get(self._source_entity_id)
        self._device = dev_reg.async_get(
            cover.device_id) if cover and cover.device_id else None

        _LOGGER.debug("[%s] Created mapped cover entity",
                      self._source_entity_id)

    async def async_will_remove_from_hass(self) -> None:
        """
        Cleanup when entity is being removed from Home Assistant.

        This is called by Home Assistant during entity removal and ensures
        proper cleanup of all async resources to prevent task warnings and
        resource leaks. Critical for integration stability.
        """
        # Cancel all running tasks to prevent orphaned coroutines
        for task in self._running_tasks:
            if not task.done():
                task.cancel()

        # Remove all state listeners to prevent callback after removal
        for remove_listener in self._state_listeners:
            remove_listener()

        # Set event to wake up any waiting coroutines so they can exit gracefully
        self._target_changed_event.set()

        # Clear collections to release references
        self._running_tasks.clear()
        self._state_listeners.clear()

        _LOGGER.debug("[%s] Cleaned up mapped cover entity",
                      self._source_entity_id)

    def _create_tracked_task(self, coro):
        """
        Create a task and track it for proper cleanup.

        This ensures all async tasks created by the entity are properly tracked
        and can be cancelled during entity removal to prevent warnings.

        Args:
          coro: Coroutine to wrap in a task

        Returns:
          asyncio.Task: The created task
        """
        task = self.hass.async_create_task(coro)
        self._running_tasks.add(task)
        # Automatically remove from tracking when task completes
        task.add_done_callback(lambda t: self._running_tasks.discard(t))
        return task

    @property
    def _source_current_position(self):
        """Get current position from source cover, handling unavailable states."""
        src = self.hass.states.get(self._source_entity_id)
        if src and src.state not in ("unavailable", "unknown"):
            return src.attributes.get("current_position")
        return None

    @property
    def _source_current_tilt_position(self):
        """Get current tilt position from source cover, handling unavailable states."""
        src = self.hass.states.get(self._source_entity_id)
        if src and src.state not in ("unavailable", "unknown"):
            return src.attributes.get("current_tilt_position")
        return None

    # Configuration property accessors - retrieve settings from config entry
    @property
    def _rename_pattern(self):
        """Regex pattern for renaming the entity (from config)."""
        return self._entry.data.get("rename_pattern", const.DEFAULT_RENAME_PATTERN)

    @property
    def _rename_replacement(self):
        """Replacement string for renaming the entity (from config)."""
        return self._entry.data.get("rename_replacement", const.DEFAULT_RENAME_REPLACEMENT)

    @property
    def _min_pos(self):
        """Minimum position value in source scale (from config)."""
        return int(self._entry.data.get("min_position", const.DEFAULT_MIN_POSITION))

    @property
    def _max_pos(self):
        """Maximum position value in source scale (from config)."""
        return int(self._entry.data.get("max_position", const.DEFAULT_MAX_POSITION))

    @property
    def _min_tilt(self):
        """Minimum tilt position value in source scale (from config)."""
        return int(self._entry.data.get("min_tilt_position", const.DEFAULT_MIN_TILT_POSITION))

    @property
    def _max_tilt(self):
        """Maximum tilt position value in source scale (from config)."""
        return int(self._entry.data.get("max_tilt_position", const.DEFAULT_MAX_TILT_POSITION))

    @property
    def _close_tilt_if_down(self):
        """Whether to close tilt before lowering position (from config)."""
        return bool(self._entry.data.get("close_tilt_if_down", const.DEFAULT_CLOSE_TILT_IF_DOWN))

    @property
    def name(self):
        """
        Generate entity name using regex pattern replacement on source device name.

        Falls back to source entity ID if no device name is available.
        Pattern replacement allows customization like "Mapped {original_name}".
        """
        return re.sub(self._rename_pattern, self._rename_replacement, self._device and self._device.name or self._source_entity_id, count=1)

    @property
    def device_info(self):
        """
        Provide device info so the entity appears grouped under this integration.

        Creates a virtual device for this mapped cover, separate from the source
        device to maintain clear organization in the UI.
        """
        return {
            "identifiers": {(const.DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Mapped Cover Integration",
            "model": "Virtual Cover",
        }

    @property
    def unique_id(self):
        """Generate unique ID combining config entry and source entity."""
        return f"{self._entry.entry_id}_{self._source_entity_id}"

    @property
    def supported_features(self):
        """
        Report supported features based on source cover capabilities.

        Only exposes features that this integration actively remaps.
        This prevents exposing unsupported features like position memory.
        """
        src = self.hass.states.get(self._source_entity_id)
        if not src:
            _LOGGER.debug(
                "[%s] Source entity not found for supported_features", self._source_entity_id)
            return 0
        features = src.attributes.get("supported_features", 0)

        # Only expose features that are remapped by this integration
        feature_mask = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION | CoverEntityFeature.STOP |
            CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT | CoverEntityFeature.SET_TILT_POSITION | CoverEntityFeature.STOP_TILT
        )
        return features & feature_mask

    @property
    def is_closed(self):
        """
        Cover is closed when both position and tilt are at minimum values.

        This follows Home Assistant convention where 0 means fully closed.
        """
        return self.current_cover_position == 0 and self.current_cover_tilt_position in (0, None)

    @property
    def is_closing(self):
        """
        Cover is closing if target position is lower than current position.

        When actively moving to a target, use target vs current comparison.
        Otherwise falls back to source cover's state.
        """
        pos = self._source_current_position
        if self._target_position is not None and self._source_current_position is not None:
            return self._target_position < pos
        return super().is_closing

    @property
    def is_opening(self):
        """
        Cover is opening if target position is higher than current position.

        When actively moving to a target, use target vs current comparison.
        Otherwise falls back to source cover's state.
        """
        pos = self._source_current_position
        if self._target_position is not None and self._source_current_position is not None:
            return self._target_position > pos
        return super().is_opening

    @property
    def current_cover_position(self):
        """
        Get current position in user scale (0-100), with target position priority.

        When a movement is in progress (_target_position is set), report the target
        position to provide immediate UI feedback. Otherwise report the actual
        current position from the source cover, remapped to user scale.

        Returns:
          int|None: Position in 0-100 scale, or None if unavailable
        """
        if self._target_position is not None:
            # During movement, report target for immediate UI feedback
            return remap_value(
                self._target_position,
                min_value=self._min_pos, max_value=self._max_pos,
                direction=RemapDirection.FROM_SOURCE
            )
        pos = self._source_current_position
        if pos is not None:
            # Remap actual source position to user scale
            return remap_value(
                pos,
                min_value=self._min_pos, max_value=self._max_pos,
                direction=RemapDirection.FROM_SOURCE
            )
        return None

    @property
    def current_cover_tilt_position(self):
        """
        Get current tilt position in user scale (0-100), with target tilt priority.

        When a tilt movement is in progress (_target_tilt is set), report the target
        tilt for immediate UI feedback. Otherwise report actual tilt from source.

        Returns:
          int|None: Tilt position in 0-100 scale, or None if unavailable
        """
        tilt = self._target_tilt
        if tilt is None:
            tilt = self._source_current_tilt_position
        if tilt is not None:
            # Remap source tilt to user scale
            tilt = remap_value(
                tilt,
                min_value=self._min_tilt, max_value=self._max_tilt,
                direction=RemapDirection.FROM_SOURCE
            )

        return tilt

    @property
    def available(self):
        """Entity is available when source cover is available and not in unknown state."""
        src = self.hass.states.get(self._source_entity_id)
        return src is not None and src.state not in ("unavailable", "unknown")

    @property
    def device_class(self):
        """
        Inherit device class from source cover for proper UI representation.

        Device class determines how the cover appears in the UI (e.g., "blind",
        "curtain", "garage"). This passes through the source cover's classification.
        """
        src = self.hass.states.get(self._source_entity_id)
        if src is not None:
            return src.attributes.get("device_class")
        return None

    @property
    def is_moving(self):
        """
        Cover is moving if recently commanded or source cover reports movement.

        Uses a time-based heuristic: if a position command was sent within the
        last 5 seconds, consider the cover moving. This provides immediate UI
        feedback before the source cover state updates.
        """
        # Consider moving if a position command was sent recently
        recently_moving = (
            time.time() - self._last_position_command) < RECENT_MOVEMENT_THRESHOLD_SECONDS
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

        remove = async_track_state_change_event(
            hass, [entity_id], state_listener)
        self._state_listeners.append(remove)  # Track for cleanup

        # Check current state immediately
        state = hass.states.get(entity_id)
        if _attr_reached(state):
            remove()
            self._state_listeners.remove(remove)
            return True
        event_wait_task = None
        try:
            event_wait_task = asyncio.create_task(event.wait())
            self._running_tasks.add(event_wait_task)  # Track for cleanup

            done, pending = await asyncio.wait(
                [fut, event_wait_task],
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel any pending tasks to prevent task cleanup warnings
            for task in pending:
                task.cancel()

            if fut in done and fut.done() and fut.result():
                return True
            return False
        finally:
            remove()
            if remove in self._state_listeners:
                self._state_listeners.remove(remove)
            if event_wait_task is not None:
                if not event_wait_task.done():
                    event_wait_task.cancel()
                if event_wait_task in self._running_tasks:
                    self._running_tasks.remove(event_wait_task)

    async def _call_service(self, command, data, retry=0, timeout=30, abort_check=None):
        """
        Asynchronously call a Home Assistant cover service with optional retries and attribute confirmation.
        Args:
          command (str): The cover service command to call. Must be one of:
            "set_cover_position", "set_cover_tilt_position", "stop_cover", or "stop_cover_tilt".
          data (dict): The service data to send with the command.
          retry (int, optional): Number of times to retry the command if the target attribute is not reached. Defaults to 0 (no retry).
          timeout (int, optional): Timeout in seconds to wait for the attribute to reach the target value after calling the service. Defaults to 30.
          abort_check (callable, optional): A function that returns True if the operation should be aborted. Defaults to None.
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

        # Update timestamp for position-related commands that cause cover movement
        # Note: tilt commands adjust slats but don't move the cover itself
        position_commands = {"set_cover_position"}
        if command in position_commands:
            self._last_position_command = time.time()

        attempt = 0
        while True:
            try:
                if abort_check and abort_check():
                    _LOGGER.debug(
                        "[%s] _call_service: Aborted calling %s", self._source_entity_id, command)
                    return False

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
                        _LOGGER.debug("[%s] _call_service: %s did not reach position %s (attempt %d)",
                                      self._source_entity_id, command, data["position"], attempt + 1)
                elif retry > 0 and command == "set_cover_tilt_position" and "tilt_position" in data:
                    reached = await self._wait_for_attribute("current_tilt_position", data["tilt_position"], timeout=timeout)
                    if reached:
                        return True
                    else:
                        _LOGGER.debug("[%s] _call_service: %s did not reach tilt %s (attempt %d)",
                                      self._source_entity_id, command, data["tilt_position"], attempt + 1)
                else:
                    return True
            except Exception as e:
                _LOGGER.warning("[%s] _call_service: Exception on %s: %s (attempt %d)",
                                self._source_entity_id, command, e, attempt + 1)
            attempt += 1
            if attempt > retry:
                if retry > 0:
                    _LOGGER.warning(
                        "[%s] _call_service: Max retries (%s) reached for %s", self._source_entity_id, retry, command)
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

        def abort_check(): return (
            self._target_position != position or
            self._target_tilt != tilt
        )

        _LOGGER.debug("[%s] converge_position: target_position=%s, target_tilt=%s, current_pos=%s",
                      self._source_entity_id, position, tilt, current_pos)
        # Set tilt first if both are set and (target position != current) and the cover is not recently moving
        if tilt is not None and position is not None and (current_pos is None or position != current_pos) and not self.is_moving:
            _LOGGER.debug(
                "[%s] Setting tilt before position: tilt_position=%s (target_position=%s)",
                self._source_entity_id, tilt, position
            )
            await self._call_service(
                "set_cover_tilt_position",
                {"entity_id": self._source_entity_id, "tilt_position": tilt},
                abort_check=abort_check,
            )
            if abort_check():
                _LOGGER.debug("[%s] converge_position: abort (position=%s, tilt=%s)",
                              self._source_entity_id, position, tilt)
                return

        current_pos = self._source_current_position

        # If the cover is moving and the target position is equal to the current position,
        # stop the cover and look for its current position again
        if self.is_moving and current_pos == position:
            _LOGGER.debug(
                "[%s] Cover is moving but already at target position, stopping", self._source_entity_id)
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
                retry=3,
                abort_check=abort_check,
            )
            self.async_write_ha_state()

        if abort_check():
            _LOGGER.debug("[%s] converge_position: abort (position=%s, tilt=%s)",
                          self._source_entity_id, position, tilt)
            return

        # Set tilt if needed
        if tilt is not None:
            current_tilt = self._source_current_tilt_position

            # Set tilt to 0 before setting the target tilt if close_tilt_if_down is enabled,
            # the cover was not moved during this converge, and target tilt position is below current position
            if self._close_tilt_if_down and position is None and tilt < current_tilt:
                await self._call_service(
                    "set_cover_tilt_position",
                    {"entity_id": self._source_entity_id, "tilt_position": 0},
                    retry=3,
                    abort_check=abort_check,
                )

                if abort_check():
                    _LOGGER.debug("[%s] converge_position: abort (position=%s, tilt=%s)",
                                  self._source_entity_id, position, tilt)
                    return

            reached = False

            if position is not None and current_pos != position:
                reached = await self._wait_for_attribute("current_tilt_position", tilt, 5)

            if not reached:
                await self._call_service(
                    "set_cover_tilt_position",
                    {"entity_id": self._source_entity_id, "tilt_position": tilt},
                    retry=3,
                    abort_check=abort_check,
                )

        self._target_position = None
        self._target_tilt = None
        self.async_write_ha_state()
        _LOGGER.debug("[%s] converge_position: DONE", self._source_entity_id)

    async def async_set_cover_position(self, **kwargs):
        position = kwargs.get("position")
        if position is None:
            _LOGGER.debug(
                "[%s] async_set_cover_position: No position provided", self._source_entity_id)
            return
        new_target = remap_value(
            position, self._min_pos, self._max_pos, direction=RemapDirection.TO_SOURCE)
        # Only call converge_position if the target is different from the current target or current position
        if self._target_position == new_target:
            _LOGGER.debug("[%s] async_set_cover_position: Target already set to %s",
                          self._source_entity_id, new_target)
            return
        current_pos = self._source_current_position
        if self._target_position is None and current_pos == new_target:
            _LOGGER.debug("[%s] async_set_cover_position: Already at target position %s",
                          self._source_entity_id, new_target)
            return
        self._target_position = new_target
        # Set current tilt as target tilt if target tilt is None
        if self._target_tilt is None:
            current_tilt = self._source_current_tilt_position
            if current_tilt is not None:
                self._target_tilt = current_tilt
        self._create_tracked_task(self.converge_position())

    async def async_set_cover_tilt_position(self, **kwargs):
        tilt = kwargs.get("tilt_position")
        if tilt is None:
            _LOGGER.debug(
                "[%s] async_set_cover_tilt_position: No tilt_position provided", self._source_entity_id)
            return
        new_target = remap_value(
            tilt, self._min_tilt, self._max_tilt, direction=RemapDirection.TO_SOURCE)
        if self._target_tilt == new_target:
            _LOGGER.debug("[%s] async_set_cover_tilt_position: Target already set to %s",
                          self._source_entity_id, new_target)
            return
        current_tilt = self._source_current_tilt_position
        if self._target_tilt is None and current_tilt == new_target:
            _LOGGER.debug("[%s] async_set_cover_tilt_position: Already at target tilt %s",
                          self._source_entity_id, new_target)
            return
        self._target_tilt = new_target
        self._create_tracked_task(self.converge_position())

    async def async_open_cover(self, **kwargs):
        features = self.supported_features

        if self._source_current_position != self._max_pos:
            self._target_position = self._max_pos
        if features & CoverEntityFeature.SET_TILT_POSITION and self._source_current_tilt_position != self._max_tilt:
            self._target_tilt = self._max_tilt
        if self._target_position is not None or self._target_tilt is not None:
            self._create_tracked_task(self.converge_position())

    async def async_close_cover(self, **kwargs):
        features = self.supported_features
        if self._source_current_position != 0:
            self._target_position = 0
        if features & CoverEntityFeature.SET_TILT_POSITION and self._source_current_tilt_position != 0:
            self._target_tilt = 0
        if self._target_position is not None or self._target_tilt is not None:
            self._create_tracked_task(self.converge_position())

    async def async_open_cover_tilt(self, **kwargs):
        if self._source_current_tilt_position != self._max_tilt:
            self._target_tilt = self._max_tilt
            self._create_tracked_task(self.converge_position())

    async def async_close_cover_tilt(self, **kwargs):
        if self._source_current_tilt_position != 0:
            self._target_tilt = 0
            self._create_tracked_task(self.converge_position())

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
