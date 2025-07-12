"""Centralized test constants for MappedCover tests.

This module contains all test constants used across the test suite.
Constants are organized by category for better maintainability.
"""

# -----------------------------------------------------------------------------
# ENTITY IDENTIFIERS
# -----------------------------------------------------------------------------

# Standard test entity IDs
TEST_ENTRY_ID = "test_entry_id"
TEST_COVER_ID = "cover.test_cover"  # Entity ID for the mapped cover
TEST_AREA_ID = "test_area"
TEST_DEVICE_NAME = "Test Source Device"
TEST_ENTITY_NAME = "Test Cover"

# -----------------------------------------------------------------------------
# COVER FEATURES
# -----------------------------------------------------------------------------

# Standard cover features bitmasks
FEATURES_BASIC = 15  # OPEN+CLOSE+SET_POSITION+STOP
FEATURES_WITH_TILT = 143  # FEATURES_BASIC + OPEN_TILT+SET_TILT_POSITION

# -----------------------------------------------------------------------------
# CONFIGURATION DATA
# -----------------------------------------------------------------------------

# Standard field lists for validation
BASIC_CONFIG_FIELDS = [
    "rename_pattern", "rename_replacement",
    "min_position", "max_position",
    "throttle"
]

TILT_CONFIG_FIELDS = [
    "min_tilt_position", "max_tilt_position",
    "close_tilt_if_down"
]

USER_STEP_FIELDS = ["label", "covers"]

# Standard configuration data for tests
STANDARD_CONFIG_DATA = {
    "rename_pattern": "^(.*)$",
    "rename_replacement": "Mapped \\1",
    "min_position": 10,
    "max_position": 90,
    "min_tilt_position": 5,
    "max_tilt_position": 95,
    "close_tilt_if_down": True,
    "throttle": 150,
}

# -----------------------------------------------------------------------------
# TEST SCENARIOS
# -----------------------------------------------------------------------------

# Standard test scenarios for attribute waiting
TEST_SCENARIO_IMMEDIATE_RETURN = "immediate_return"
TEST_SCENARIO_TIMEOUT = "timeout"
TEST_SCENARIO_UNAVAILABLE_STATE = "unavailable_state"
TEST_SCENARIO_MISSING_ATTRIBUTE = "missing_attribute"
TEST_SCENARIO_STATE_CHANGE = "state_change"
TEST_SCENARIO_EARLY_EXIT = "early_exit"

# -----------------------------------------------------------------------------
# TIME CONSTANTS
# -----------------------------------------------------------------------------

# Standard timeouts and delays
DEFAULT_TIMEOUT = 5.0
DEFAULT_DELAY = 0.1
CONVERGENCE_TIMEOUT = 10.0
ATTRIBUTE_WAIT_TIMEOUT = 5.0

# -----------------------------------------------------------------------------
# POSITION AND TILT VALUES
# -----------------------------------------------------------------------------

# Standard position and tilt values for testing
POSITION_CLOSED = 0
POSITION_OPEN = 100
POSITION_MIDDLE = 50
TILT_CLOSED = 0
TILT_OPEN = 100
TILT_MIDDLE = 50

# -----------------------------------------------------------------------------
# DEVICE INFORMATION
# -----------------------------------------------------------------------------

# Standard device information
TEST_MANUFACTURER = "Test Manufacturer"
TEST_MODEL = "Test Model"
TEST_SW_VERSION = "1.0.0"
TEST_HW_VERSION = "1.0"
TEST_VIA_DEVICE = "Test Via Device"
