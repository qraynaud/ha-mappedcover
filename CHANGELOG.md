# Changelog

All notable changes to this project will be documented in this file.

## [0.4.4] - 2025-07-12
### Changed
- Add test coverage.
- If the current (tilt) position is below min, display it as 1 and not 0.
- Fixes issues found thanks to the tests.
- Fixes the cleanup that did not cancel timers properly
- Change indentation size in .editorconfig from 2 to 4 spaces for consistency.
- Add .coverage to .gitignore to prevent coverage files from being tracked.
- Introduce LICENSE file with MIT License details.
- Enhance README.md with a Table of Contents and improved license reference.
- Update requirements-dev.txt to include pytest-check for better testing capabilities.
- Remove outdated TODO.md file.
- Introduce basic rules for code style in .cursor/rules/basic.mdc.
- Add centralized test constants in tests/constants.py for better maintainability.
- Refactor test fixtures and helpers for improved organization and clarity.

## [0.4.3] - 2025-06-01
### Changed
- Improved abort logic in mapped cover operations: service calls now reliably abort if the target position or tilt changes during execution.
- Improved reliability and maintainability of mapped cover convergence logic.

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
