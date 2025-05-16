# mappedcover

## Overview
`ha-mappedcover` is a Home Assistant custom integration that lets you create a virtual cover entity based on an existing one, with remapped position and tilt ranges. This is useful if you want to limit the movement or tilt range of a physical cover, or present a different range to Home Assistant automations and dashboards.

## Features
- Select an existing cover during setup (excluding already-mapped covers).
- Remap the maximum and minimum positions (excluding 0, which always maps to 0; 1–100 maps linearly to your min/max).
- Remap the maximum and minimum tilt positions if the selected cover supports tilt (same logic as above).
- The virtual cover always reports the target position/tilt as its current state while moving, making automations and dashboards more responsive.
- Covers with open tilts are never reported as closed.
- All configuration and reconfiguration can be done via the Home Assistant UI (Config Flow/Options Flow).
- HACS-compatible structure.

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
2. Select the physical cover to map.
3. Set the name and remapping options for position and (if available) tilt.
4. Save. A new virtual cover entity will be created.
5. You can reconfigure the mapping (including min/max, name, and tilt) at any time from the integration's options panel.

## Usage
After setup, a new cover entity will appear in Home Assistant. Use this entity in automations and dashboards as you would any other cover. The entity will:
- Forward all commands to the underlying cover, remapping values as configured.
- Always report the target position/tilt as its state while moving, and sync with the real cover when not moving.

## Remapping Logic
- **Position**: 0 always maps to 0. 1–100 maps linearly to your configured min/max.
- **Tilt**: Same as position, if supported by the underlying cover.

## Development
- `__init__.py`: Integration setup and platform forwarding.
- `manifest.json`: Integration metadata.
- `sensor.py`: Implements the mapped cover cover entity and remapping logic.
- `const.py`: Constants for config keys and domain.
- `config_flow.py`: UI-based configuration and options flow.
- `strings.json`: User-facing strings for config flow.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.