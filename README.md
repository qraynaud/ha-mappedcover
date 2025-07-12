# mappedcover

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Remapping Logic](#remapping-logic)
- [Name Remapping](#name-remapping)
- [Examples](#examples)
- [Frequently Asked Questions](#frequently-asked-questions)
- [Development & Contributing](#development--contributing)
- [License](#license)

## Overview
`ha-mappedcover` is a Home Assistant custom integration that creates virtual cover entities with **limited position and tilt ranges** based on your existing covers.

**Why use this?** If you have covers that can open 0-100% but you only want to use 25-75% for safety, privacy, or mechanical reasons, this integration creates a new cover entity that maps 0-100% user commands to your desired 25-75% physical range.

Perfect for child safety, privacy controls, preventing glare, or protecting aging cover mechanisms.

## Features
- **Range Limiting**: Map 0-100% user commands to any physical range (e.g., 25-75%)
- **Multi-Cover Setup**: Configure multiple covers at once with identical settings
- **Smart Name Generation**: Automatically rename covers using regex patterns
- **Tilt Support**: Limit tilt ranges for venetian blinds and similar covers
- **Area Inheritance**: Mapped covers automatically join the same area as source covers
- **UI Configuration**: Complete setup and reconfiguration through Home Assistant UI
- **Device Throttling**: Configurable delays to protect motorized covers (or bad box implementations) from overload
- **HACS Ready**: Easy installation through Home Assistant Community Store

## Installation

### HACS (Recommended)
[![Open your Home Assistant instance and show the add repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=qraynaud&repository=ha-mappedcover&category=integration)

1. Open HACS in Home Assistant.
2. Click the button above or add this repository as a custom integration in HACS.
3. Search for "Mapped Cover" and install.
4. Restart Home Assistant.

### Manual Installation
1. Download or clone this repository.
2. Copy the `custom_components/mappedcover` folder into your Home Assistant `custom_components` directory (usually `/config/custom_components/`).
3. Restart Home Assistant.

## Configuration

### Step-by-Step Setup

Configuration is done entirely through the Home Assistant UI:

1. **Add Integration**: Go to **Settings > Devices & Services > Add Integration** and search for "Mapped Cover"
2. **Select Covers**: Choose one or more physical covers to map (already-mapped covers are excluded)
3. **Configure Mapping**: Set name patterns and remapping ranges
4. **Save**: New mapped cover entities will be created automatically

### Configuration Options

#### Basic Configuration
- **Label**: A descriptive name for this group of mapped covers
- **Covers**: Select one or more existing cover entities to map (already-mapped covers are automatically excluded)

#### Name Mapping (Regex)
- **Rename Pattern**: Regular expression to match cover names (default: `^.*$` matches everything)
- **Rename Replacement**: Replacement text with group references (default: `Mapped \g<0>` adds "Mapped" prefix)

#### Position Remapping
- **Min Position**: Minimum physical position your cover will move to (0-100, default: 0)
- **Max Position**: Maximum physical position your cover will move to (0-100, default: 100)

*Example: Min=25, Max=75 means when you command 100% open, the cover only opens to 75%*

#### Tilt Remapping (appears only if selected covers support tilt)
- **Min Tilt Position**: Minimum physical tilt angle (0-100, default: 0)
- **Max Tilt Position**: Maximum physical tilt angle (0-100, default: 100)

#### Advanced Options
- **Close Tilt if Down**: When cover moves down, automatically close tilt first (default: True)
- **Throttle**: Minimum milliseconds between commands to prevent device overload (default: 100)

### Reconfiguration

You can modify any settings at any time:
1. Go to **Settings > Devices & Services > Mapped Cover**
2. Click **Configure** on any mapped cover entry
3. Update settings and save - changes apply immediately

## Usage

### Entity Behavior
After setup, new cover entities appear with names based on your regex pattern:

#### Movement and State Reporting
- **While Moving**: Shows target position/tilt values immediately
- **When Stationary**: Shows actual remapped values from the physical cover
- **Movement Detection**: Based on recent commands (5-second window) or underlying cover state

#### Command Processing
- **Position Commands**: Remapped and sent to physical cover with throttling
- **Tilt Commands**: Remapped only if the underlying cover supports tilt
- **Stop Commands**: Immediately forwarded to physical cover
- **Area Assignment**: Automatically inherits area from the underlying cover

#### Error Handling
- **Unavailable Covers**: Mapped covers show as unavailable when source is unavailable
- **Service Failures**: Retries with exponential backoff, then logs errors
- **Network Issues**: Graceful degradation with last known state

### Quick Start Guide
1. **Install** the integration via HACS or manually
2. **Add Integration** through Settings → Devices & Services
3. **Select covers** you want to limit/remap
4. **Set ranges** (e.g., Min: 0, Max: 50 for 50% maximum opening)
5. **Choose names** using regex patterns
6. **Save** and start using your new limited covers

### Troubleshooting
- **Covers not appearing**: Check that source covers are not already mapped
- **Wrong positions**: Verify your min/max settings match your expectations
- **Slow response**: Adjust throttle settings or check network connectivity
- **Name conflicts**: Ensure regex replacement creates unique names

## Remapping Logic

Understanding how position mapping works is key to using this integration effectively.

### The Core Concept
- **0% always means fully closed** - this never changes
- **1-100% gets remapped** to your configured physical range
- **Physical values get mapped back** to 1-100% for display

### Position Mapping Examples

#### Example: 25-75% Physical Range
```
Your Command → Physical Position → What You See
0%          → 0%               → 0%
1%          → 25%              → 1%
50%         → 50%              → 50%
100%        → 75%              → 100%
```

If the physical cover reports 60%, you'll see 70% in Home Assistant.

#### Example: 0-50% Physical Range
```
Your Command → Physical Position → What You See
0%          → 0%               → 0%
1%          → 0%               → 1%
50%         → 25%              → 50%
100%        → 50%              → 100%
```

#### Example: 10-90% Physical Range
```
Your Command → Physical Position → What You See
0%          → 0%               → 0%
1%          → 10%              → 1%
50%         → 50%              → 50%
100%        → 90%              → 100%
```

### Mathematical Formulas

**User to Physical (TO_SOURCE):**
- If user_value = 0: `physical = 0`
- If user_value = 1-100: `physical = min_pos + (user_value - 1) × (max_pos - min_pos) / 99`

**Physical to User (FROM_SOURCE):**
- If physical = 0: `user = 0`
- If physical < min_pos: `user = 1`
- If physical ≥ min_pos: `user = 1 + (physical - min_pos) × 99 / (max_pos - min_pos)`

### Tilt Mapping
Tilt follows identical logic to position mapping when the cover supports tilt.

### Special Cases
- **Values below minimum**: Physical positions below your min setting display as 1% (not 0%)
- **Equal min/max**: If min=max, all commands map to 0% physical position
- **Full range (0-100)**: Behaves almost like a pass-through with minor rounding

## Name Remapping

You can automatically rename your mapped covers using regular expressions:

- **rename_pattern**: A regular expression pattern that matches part or all of the original cover name
- **rename_replacement**: The replacement string for the matched pattern (supports group references)

### Regex Pattern Examples

#### Simple Prefix Example
- **Original**: `Living Room Window`
- **Pattern**: `^.*$`
- **Replacement**: `Mapped \g<0>`
- **Result**: `Mapped Living Room Window`

#### Extract Room Name Example
- **Original**: `Cover Living Room`
- **Pattern**: `^Cover (.*)$`
- **Replacement**: `Limited \g<1> Blinds`
- **Result**: `Limited Living Room Blinds`

#### Replace Specific Words Example
- **Original**: `Bedroom Roller Shutter`
- **Pattern**: `^(.*) Roller (.*)$`
- **Replacement**: `\g<1> Partial \g<2>`
- **Result**: `Bedroom Partial Shutter`

#### Multiple Covers Example
For covers named `Office Blind`, `Kitchen Blind`, `Bedroom Blind`:
- **Pattern**: `^(.*) Blind$`
- **Replacement**: `\g<1> Limited Blind`
- **Results**: `Office Limited Blind`, `Kitchen Limited Blind`, `Bedroom Limited Blind`

### Regex Reference
- `\g<0>`: Entire matched name
- `\g<1>`, `\g<2>`, etc.: Captured groups in parentheses
- `^`: Start of string
- `$`: End of string
- `.*`: Match any characters
- `(.*)`: Capture any characters in a group

## Examples

### Example 1: Child Safety Window Limiters

**Scenario**: Bedroom windows that shouldn't open more than 30% for child safety.

**Configuration**:
```yaml
Label: "Child-Safe Windows"
Covers: ["cover.bedroom_window", "cover.nursery_window"]
Rename Pattern: "^(.*) Window$"
Rename Replacement: "Safe \g<1> Window"
Min Position: 0
Max Position: 30
```

**Result**:
- New entities: `cover.safe_bedroom_window`, `cover.safe_nursery_window`
- When you set 100% open → Physical window opens to only 30%
- When you set 50% open → Physical window opens to 15%
- Physical window at 20% → Shows as 67% in Home Assistant
- Full automation support with safety built-in

### Example 2: Anti-Glare Office Blinds

**Scenario**: Venetian blinds that can tilt 0-90°, but you want to prevent harsh glare by limiting tilt to 20-60°.

**Configuration**:
```yaml
Label: "Anti-Glare Blinds"
Covers: ["cover.office_venetian"]
Rename Pattern: "^(.*)$"
Rename Replacement: "Anti-Glare \g<0>"
Min Position: 0
Max Position: 100
Min Tilt Position: 20
Max Tilt Position: 60
Close Tilt if Down: true
```

**Result**:
- New entity: `cover.anti_glare_office_venetian`
- Position works normally (0-100% → 0-100%)
- Tilt commands 0-100% → Physical tilt 20-60°
- Tilt command 100% → Physical tilt 60° (not 90°)
- When closing position, tilt goes to 20° first (if enabled)

### Example 3: Privacy Bedroom Covers

**Scenario**: Bedroom covers that should never open fully for privacy, limiting to 40% maximum.

**Configuration**:
```yaml
Label: "Privacy Covers"
Covers: ["cover.master_bedroom_blind", "cover.guest_bedroom_blind"]
Rename Pattern: "^(.*) Bedroom (.*)$"
Rename Replacement: "Private \g<1> \g<2>"
Min Position: 0
Max Position: 40
Throttle: 300
```

**Result**:
- New entities: `cover.private_master_blind`, `cover.private_guest_blind`
- Commands throttled to 300ms intervals for quiet operation
- Maximum opening limited to 40% physical position
- Perfect for automations that won't compromise privacy

### Example 4: Mechanical Protection

**Scenario**: Older motorized blinds that strain at full extension - limit to 10-85% to protect mechanisms.

**Configuration**:
```yaml
Label: "Protected Vintage Blinds"
Covers: ["cover.vintage_motorized_1", "cover.vintage_motorized_2"]
Rename Pattern: "^Vintage (.*)$"
Rename Replacement: "Protected \g<1>"
Min Position: 10
Max Position: 85
Throttle: 1000
```

**Result**:
- Never moves to true 0% or 100% to protect aging mechanisms
- Slow 1-second throttling for gentle operation
- Command 0% → Physical 0%, Command 100% → Physical 85%
- Command 50% → Physical ~47% (mid-point of 10-85% range)

### Advanced Example: Automated Light Control System

**Scenario**: Office building with 50 windows that need coordinated light control throughout the day.

**Configuration**:
```yaml
# Morning Setup (6 AM - 12 PM)
Label: "Morning Light Control"
Covers: ["cover.east_window_1", "cover.east_window_2", ..., "cover.east_window_15"]
Rename Pattern: "^(.*)_window_(.*)$"
Rename Replacement: "Morning_\g<1>_\g<2>"
Min Position: 0
Max Position: 60
Min Tilt Position: 30
Max Tilt Position: 70

# Afternoon Setup (12 PM - 6 PM)
Label: "Afternoon Glare Control"
Covers: ["cover.south_window_1", "cover.south_window_2", ..., "cover.south_window_20"]
Rename Pattern: "^(.*)_window_(.*)$"
Rename Replacement: "Afternoon_\g<1>_\g<2>"
Min Position: 10
Max Position: 40
Min Tilt Position: 10
Max Tilt Position: 45
```

**Automation Integration**:
```yaml
# Example Home Assistant automation
automation:
  - alias: "Adaptive Office Lighting"
    trigger:
      - platform: sun
        event: sunrise
    action:
      - service: cover.set_cover_position
        target:
          entity_id: "cover.morning_east_*"
        data:
          position: 80  # Maps to 48% physical position
  - alias: "Prevent Afternoon Glare"
    trigger:
      - platform: time
        at: "12:00:00"
    action:
      - service: cover.set_cover_position
        target:
          entity_id: "cover.afternoon_south_*"
        data:
          position: 50  # Maps to 25% physical position
```

**Result**:
- 35 mapped entities with time-appropriate limits
- Automations can use full 0-100% range safely
- Physical covers never exceed optimal positions
- Coordinated light management across entire building

## Development & Contributing

### Project Structure
```
custom_components/mappedcover/
├── __init__.py          # Integration setup and platform forwarding
├── manifest.json        # Integration metadata and dependencies
├── cover.py            # Core MappedCover entity and remapping logic
├── const.py            # Constants and default values
├── config_flow.py      # UI configuration flow with validation
└── translations/       # Localization files
    └── en.json         # English UI strings
```

### Key Components
- **`MappedCover` Entity**: Main cover implementation with state management
- **`remap_value()` Function**: Core mathematical remapping between ranges
- **Config Flow**: User-friendly setup and reconfiguration interface
- **Area Management**: Automatic device and area assignment
- **Throttling System**: Rate limiting for device protection

### Testing
The project includes comprehensive test coverage:
- **124 test cases** across config flows and entity behavior
- **Integration tests** with real Home Assistant instances
- **Unit tests** for remapping logic and edge cases
- **Mock testing** for service calls and state management

Run tests with: `python -m pytest tests/`

### Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Write tests for new functionality
4. Ensure all tests pass: `pytest tests/`
5. Update documentation as needed
6. Submit a pull request

### Local Development
```bash
# Clone repository
git clone https://github.com/qraynaud/ha-mappedcover.git
cd ha-mappedcover

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=custom_components.mappedcover
```

## Frequently Asked Questions

### General Questions

**Q: What happens to my automations when I switch to mapped covers?**
A: Update your automations to use the new mapped cover entities. The benefit is that automations can safely use 0-100% ranges knowing they won't exceed your configured limits.

**Q: Can I map covers that are already mapped?**
A: No, the integration automatically excludes already-mapped covers to prevent recursion and conflicts.

**Q: Do mapped covers support all the same features as original covers?**
A: Yes, mapped covers support position, tilt (if source supports it), opening, closing, and stopping. Features are automatically detected from the source cover.

### Configuration Questions

**Q: What if I set Min Position > Max Position accidentally?**
A: The integration handles this gracefully by clamping values, but your configuration should be corrected for predictable behavior.

**Q: Can I have different settings for position and tilt?**
A: Yes! Position and tilt are configured independently. You can limit tilt to 20-60° while leaving position at 0-100%.

**Q: How do I undo/remove a mapped cover?**
A: Go to Settings → Devices & Services → Mapped Cover, click the integration entry, and delete it. The mapped entities will be removed automatically.

### Technical Questions

**Q: Why does my 50% command result in 47% physical position?**
A: This is normal due to the linear mapping formula and rounding. The difference is usually 1-2% and doesn't affect functionality.

**Q: What happens if the source cover becomes unavailable?**
A: The mapped cover will also show as unavailable. When the source comes back online, the mapped cover will resume normal operation.

**Q: Does throttling affect responsiveness?**
A: Throttling adds a small delay between commands to protect devices. Default 100ms is imperceptible to users but prevents device overload.

### Troubleshooting

**Q: My mapped cover shows the wrong position**
A: Check your Min/Max settings and verify the source cover is reporting correct positions. Use Developer Tools to inspect entity states.

**Q: Commands seem delayed or don't work**
A: Check throttle settings, verify network connectivity, and ensure the source cover entity is functioning properly.

**Q: Regex naming isn't working as expected**
A: Test your regex patterns using online tools. Remember that `\g<0>` captures the entire match, while `\g<1>`, `\g<2>` capture specific groups.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

---

**Support**: If you find this integration useful, please consider starring the repository or contributing improvements!
