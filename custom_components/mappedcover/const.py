"""
Constants for the mappedcover integration.

This module defines all configuration defaults and constant values used
throughout the integration. Centralizing constants here makes it easier
to maintain consistent behavior and modify defaults.
"""

# Integration identification
DOMAIN = "mappedcover"

# UI and naming defaults
DEFAULT_LABEL = "Covers"  # Default integration instance name
DEFAULT_RENAME_PATTERN = "^.*$"  # Regex pattern to match source cover names
# Replacement pattern for mapped cover names
DEFAULT_RENAME_REPLACEMENT = "Mapped \\g<0>"

# Position mapping defaults - defines the source cover's "usable" range
# Minimum position value on source cover (fully closed)
DEFAULT_MIN_POSITION = 0
# Maximum position value on source cover (fully open)
DEFAULT_MAX_POSITION = 100

# Tilt mapping defaults - defines the source cover's tilt range
DEFAULT_MIN_TILT_POSITION = 0    # Minimum tilt position (fully closed/down)
DEFAULT_MAX_TILT_POSITION = 100  # Maximum tilt position (fully open/up)

# Behavior options
DEFAULT_CLOSE_TILT_IF_DOWN = True  # Close tilt before lowering position
DEFAULT_THROTTLE = 100  # Throttle delay in milliseconds between service calls
