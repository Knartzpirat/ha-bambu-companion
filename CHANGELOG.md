# Changelog

All notable changes to the Bambu Companion project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.0.5] — 2026-04-27

### Fixed
- **Critical structure bug:** 9 coordinator methods (runtime tracking, maintenance system, all reset functions) were nested as dead code inside the module-level `_extract_plate_info` function and not callable at runtime. This would have caused severe errors in all maintenance and reset operations.
- N3 graceful degradation completed: `printer_offline` flag is now also returned in the result dict during normal operation, allowing entities to consistently access the key.

### Technical Details
- **Affected files:** `coordinator.py`
- **Fix type:** Critical bugfix (prevents runtime errors)
- **Verification:** Python AST structure validated, all 22 coordinator methods are now proper class methods

## [0.0.4] — 2026-04-26

### Added
- Select + Button pattern for maintenance resets: A dropdown to choose the maintenance task + a button to reset it
- Extraction of plate number and project name from `gcode_file` paths for print records
- Complete translation system with German and English

### Changed
- Converted strings in `strings.json`, `options_flow.py`, and UI components from German to English
- Updated README: Untested markers for all printers except H2D, English tab names in options table
- Extended `PLATFORMS` with `"select"`

### Fixed
- Removed duplicate classes and functions (`BambuPrintTrackerOptionsFlow`, `_async_options_updated`)
- Cleaned up dead constants