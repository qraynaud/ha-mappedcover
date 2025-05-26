# mappedcover

## Overview
`ha-mappedcover` is a Home Assistant custom integration that lets you create one or more virtual ("mapped") cover entities based on existing covers, with remapped position and tilt ranges. This is useful if you want to limit the movement or tilt range of a physical cover, or present a different range to Home Assistant automations and dashboards.

## Features
- Select one or more existing covers during setup (excluding already-mapped covers).
- Remap the maximum and minimum positions (excluding 0, which always maps to 0; 1–100 maps linearly to your min/max).
- Remap the maximum and minimum tilt positions if any selected cover supports tilt (same logic as above).
- Automatically rename mapped covers using regular expressions (`rename_pattern` and `rename_replacement`).
- Mapped covers are automatically assigned to the same area as their underlying covers.
- Robust entity and device cleanup when covers are removed or the integration is reconfigured.
- All configuration and reconfiguration can be done via the Home Assistant UI (Config Flow/Options Flow).
- HACS-compatible structure.
- Throttle: You can define the minimum interval (in milliseconds) between calls to the underlying covers. This helps prevent rate-limiting or overloading physical devices.

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
Configuration is done via the Home Assistant UI:
1. Go to **Settings > Devices & Services > Add Integration** and search for "Mapped Cover".
2. Select one or more physical covers to map (already-mapped covers are excluded from selection).
3. Set the name and remapping options for position and (if available) tilt. Tilt options are shown if any selected cover supports tilt.
4. Save. New mapped cover entities will be created.
5. You can reconfigure the mapping (including min/max, name, and tilt) at any time from the integration's options panel.

## Usage
After setup, new cover entities will appear in Home Assistant. Use these entities in automations and dashboards as you would any other cover. Each mapped cover will:
- Forward all commands to the underlying cover, remapping values as configured.
- Always report the target position/tilt as its state while moving, and sync with the real cover when not moving.
- Be assigned to the same area as the underlying cover (unless you manually change the area).

## Remapping Logic
- **Position**: 0 always maps to 0. 1–100 maps linearly to your configured min/max.
- **Tilt**: Same as position, if supported by the underlying cover.

## Name Remapping

You can automatically rename your mapped covers using regular expressions:

- **rename_pattern**: A regular expression pattern that matches part or all of the original cover name.
- **rename_replacement**: The replacement string for the matched pattern.
  You can use group references (e.g., `\g<1>`) and `\g<0>` for the whole match, following Python’s `re.sub` syntax.

**Example:**
- If your original cover is named `Living Room Window` and you set:
  - `rename_pattern`: `^.*$`
  - `rename_replacement`: `Mapped \g<0>`
- The mapped cover will be named: `Mapped Living Room Window`

This allows you to create consistent, descriptive names for your mapped covers automatically.

> **Note:**
> Use `\g<0>` in the replacement string to refer to the entire matched name.
> Standard Python regular expression syntax applies.
> Only one replacement will be made if the regular expression matches multiple times

## Development
- `__init__.py`: Integration setup and platform forwarding.
- `manifest.json`: Integration metadata.
- `cover.py`: Implements the mapped cover entity, remapping logic, area assignment, and cleanup.
- `const.py`: Constants for config keys and domain.
- `config_flow.py`: UI-based configuration and options flow.
- `translations/`: User-facing strings for config flow (e.g., `en.json`).

## License
This project is licensed under the MIT License. See the LICENSE file for more details.
