# MappedCover Integration Test Plan

This document outlines the comprehensive test plan for the mappedcover Home Assistant integration. It serves as a reference for understanding the test structure and coverage of the integration's functionality.

## Legend

- [ ] Test to be written
- [x] Test implemented and passing
- [e] Test implemented but not passing
- [r] Test implemented but needing a review because of active changes
- [d] Test implemented but deprecated and needing to be removed

## Configuration Flow Tests

### test_config_flow.py - Main Config Flow Testing (16 tests)

- **Basic UI Flow**
  - [x] Test that the config flow shows user step with label and covers fields
  - [x] Test that only valid, non-mapped cover entities are selectable (exclude existing mapped covers)
  - [x] Test that configure step shows remapping fields with conditional tilt support
  - [x] Test that submitting the two-step config flow creates an entry with the correct data
  - [x] Test that min/max values are validated (throw exceptions for invalid ranges)
  - [x] Test that tilt options are only shown if the selected entity supports tilt

- **Error Handling & Edge Cases**
  - [x] Test error handling when entity registry access fails (internal_error abort)
  - [x] Test edge case: no covers available to select
  - [x] Test edge case: mixed tilt support (some covers support tilt, others don't)

- **Input Validation**
  - [x] Test validation that at least one cover is selected (vol.Length(min=1))
  - [x] Test voluptuous range validation edge cases (exactly 0, exactly 100)
  - [x] Test string field validation (empty label, malformed regex patterns)

- **Default Values & Configuration**
  - [x] Test default values are properly applied from constants
  - [x] Test optional fields have correct defaults (close_tilt_if_down, throttle)

- **Helper Functions**
  - [x] Test supports_tilt function error handling (missing state, malformed attributes)
  - [x] Test build_remap_schema with various tilt_supported scenarios

### test_reconfigure_flow.py - Reconfiguration Flow Testing (8 tests)

- **Basic Reconfiguration**
  - [x] Test that the reconfigure flow can be started for an existing mapped cover
  - [x] Test that reconfigure flow shows existing values and allows modification
  - [x] Test that reconfigure uses async_update_reload_and_abort to apply changes
  - [x] Test that changes persist after reconfiguration

- **Advanced Reconfiguration**
  - [x] Test reconfigure step with unique_id handling and mismatch abort
  - [x] Test reconfigure preserves existing entry data and title
  - [x] Test reconfigure redirects through user step correctly
  - [x] Test reconfigure vs new entry code paths in async_step_configure

## Cover Entity Tests

### test_integration_setup.py - Integration Setup Testing (3 tests)

- [x] Test that the integration loads successfully
- [x] Test that the domain is correctly registered
- [x] Test that the config flow is properly configured

### test_entity_management.py - Platform and Entity Management Testing (4 tests)

- [x] Test `async_setup_entry` creates mapped entities for all configured covers
- [x] Test entity removal and device cleanup when covers are removed from config
- [x] Test area assignment from source entity/device to mapped entity
- [x] Test `async_unload_entry` properly clean up entities

### test_entity_creation.py - Entity Creation and Initialization Testing (13 tests)

- [x] Test `MappedCover.__init__` correctly initializes with hass, entry, cover, throttler
- [x] Test unique_id generation format: `{entry_id}_{source_entity_id}`
- [x] Test device_info creation with correct identifiers and metadata
- [x] Test name generation using regex pattern/replacement from config
- [x] Test entity availability based on underlying cover state (not "unavailable"/"unknown")

### test_remapping_logic.py - Remapping Logic Testing (remap_value function)

- [x] Test `RemapDirection.TO_SOURCE`: user 0→0, 1-100→min_value..max_value linearly
- [x] Test `RemapDirection.FROM_SOURCE`: source 0→0, source<min_value→1, min_value..max_value→1-100 linearly
- [x] Test edge cases: None input, min_value==max_value, boundary values
- [x] Test rounding and clamping behavior (returns integers, clamps to valid ranges)
- [x] Test below-minimum handling: source values < min_value return 1 (not 0) in FROM_SOURCE direction

### test_property_logic.py - Property Logic Testing (62 tests)

- [x] Test `current_cover_position` returns target while moving, remapped source when static
- [x] Test `current_cover_tilt_position` returns target while moving, remapped source when static
- [x] Test `supported_features` masks only relevant cover features (position, tilt, open, close, stop)
- [x] Test `is_closed` returns True only when position=0 and tilt=0 or None
- [x] Test `is_closing`/`is_opening` based on target vs current position comparison
- [x] Test `device_class` reflection from underlying cover
- [x] Test `is_moving` logic: recently_moving (5s after command) OR cover state OPENING/CLOSING
- [x] Test `available`: should be False if the state of the underlying cover is not available and True otherwise
- [x] Test `unique_id`: should produce a proper unique_id that will be tied to the underlying cover
- [x] Test `name`: should produce a name mapped using the config regexps
- [x] Test `device_info`: should provide the necessary data for Home Assistant to create a unique device of each cover

### test_command_processing.py - Command Processing and Target Management Testing (45 tests)

- [x] Test `async_set_cover_position` sets target_position and triggers convergence
- [x] Test `async_set_cover_tilt_position` sets target_tilt and triggers convergence
- [x] Test commands skip convergence if target already matches new value
- [x] Test commands skip convergence if current position already matches target
- [x] Test `async_open_cover` sets max position/tilt targets
- [x] Test `async_close_cover` sets zero position/tilt targets
- [x] Test `async_stop_cover` clears targets and calls stop service
- [x] Test `async_stop_cover_tilt` clears tilt target and calls stop_tilt service
- [x] Test `_last_position_command` timestamp tracking in command processing context

### test_convergence_logic.py - Convergence Logic Testing (converge_position)

- [x] Test target_changed_event is raised to interrupt other waits
- [x] Test tilt-first logic: when both position+tilt set, position≠current, not recently moving
- [x] Test stop-if-moving logic: stops cover if moving but already at target position
- [x] Test position convergence with retry=3 on failure
- [x] Test tilt convergence with retry=3 on failure
- [x] Test `close_tilt_if_down` behavior: sets tilt=0 before target when tilt decreasing
- [x] Test abort logic: exits early if targets change during execution
- [x] Test target cleanup: sets _target_position and _target_tilt to None when done

### test_service_calls.py - Service Call Logic Testing (_call_service) (19 tests)

- [x] Test throttling with asyncio_throttle.Throttler
- [x] Test allowed commands validation (set_cover_position, set_cover_tilt_position, stop_cover, stop_cover_tilt)
- [x] Test position confirmation with `_wait_for_attribute` when retry>0
- [x] Test tilt confirmation with `_wait_for_attribute` when retry>0
- [x] Test retry logic with abort_check function
- [x] Test exception handling and logging on service failures
- [x] Test `_last_position_command` timestamp tracking in service call context

### test_attribute_waiting.py - Attribute Waiting Logic Testing (_wait_for_attribute)

- [x] Test waits for underlying cover attribute to match target value
- [x] Test timeout behavior (default 30s)
- [x] Test early exit when target_changed_event is set
- [x] Test custom comparison function (default: abs(val-target)<=1)
- [x] Test state change listener and immediate state checking

### test_throttling_concurrency.py - Throttling and Concurrency Testing

- [x] Test Throttler integration limits service call frequency
- [x] Test multiple converge_position calls: new targets interrupt previous runs
- [x] Test target_changed_event coordination between operations
- [x] Test async task creation for converge_position doesn't block commands

### test_error_handling.py - Error and Edge Case Handling Testing (22 tests)

- [x] Test handling of unavailable/unknown underlying cover states
- [x] Test missing source entity scenarios
- [x] Test device_id safety when source entity has no device
- [x] Test malformed source entity attributes (missing position/tilt)
- [x] Test service call failures and retry exhaustion
- [x] Test timeout scenarios in attribute waiting

### test_state_synchronization.py - State Synchronization and Reporting Testing (12 tests)

- [x] Test state reporting during movement (target values)
- [x] Test state reporting when static (actual source values, remapped)
- [x] Test async_write_ha_state calls at appropriate times
- [x] Test last_position_command timestamp tracking for is_moving
- [x] Test position command timestamp updates through _call_service
- [x] Test tilt commands do NOT update movement timestamp (semantic change)
- [x] Test open/close commands set target values correctly
- [x] Test static state transitions with proper timestamp handling
- [x] Test full movement cycle with correct remapping calculations

### test_configuration_access.py - Configuration Property Access Testing (23 tests)

- [x] Test property access for config values: rename_pattern, rename_replacement
- [x] Test property access for remapping ranges: min_pos, max_pos, min_tilt, max_tilt
- [x] Test property access for behavior flags: close_tilt_if_down
- [x] Test default value fallbacks when config missing
- [x] Test type conversion for position/tilt values to int and boolean conversion
- [x] Test edge cases: boundary values, inverted ranges, equal ranges, empty patterns
