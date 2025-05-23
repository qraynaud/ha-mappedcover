# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] - 2025-05-23
### Changed
- The `is_closed` property now returns True only if the mapped position is 0 and the mapped tilt is 0 or not present (`None`). This makes the closed state stricter and more accurate for covers with tilt.

## [0.2.0] - 2025-05-20
### Changed
- Refactored state handling: now uses `is_closed`, `is_closing`, and `is_opening` for mapped covers, matching Home Assistant best practices.
- `is_closing` and `is_opening` now return True as soon as a target position is set, regardless of actual movement.

## [0.1.0] - 2025-04-10
### Added
- Initial release: basic mapped cover functionality, position remapping, config flow, and HACS compatibility.
