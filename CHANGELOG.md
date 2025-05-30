# Changelog

All notable changes to this project will be documented in this file.

## [0.4.2] - 2025-05-30
### Changed
- Fixed a regression caused by 0.4.1 causing an exception to be raised for some tilt changes

## [0.4.1] - 2025-05-30
### Changed
- Improved error handling for cover service calls: exceptions are now caught and logged, preventing crashes on service failures.
- Reduced retry count for position/tilt commands to 3 (was 10), making the system more responsive to persistent errors.
- No functional changes except for error handling and retry logic in mapped cover operations.

## [0.4.0] - 2025-05-26
### Added
- Throttling support for mapped covers: you can now set a minimum interval (in milliseconds) between calls to the underlying covers using the new `throttle` option in the config/options flow.
- New config option and translation for `throttle` (minimum interval between calls).

## [0.3.0] - 2025-05-23
### Changed
- Comprehensive and consistent logging improvements throughout `cover.py`:
  - All log messages now use the format `[<entity_id>] xxx` for clarity.
  - Improved logging for async methods, state transitions, and aborts/interruption of actions.
- Internal refactoring to mitigate issues when handling lots of covers simultaneously.

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
