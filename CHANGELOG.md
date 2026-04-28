# Changelog

All notable changes to the Bambu Companion project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.0.6] — 2026-04-28

### Added
- **Dynamisches Düsen-Slot-System:** Jede physische Düse erhält einen eigenen Stundenzähler. Nutzer können Düsen nummerieren und über ein Select-Dropdown die aktive Düse wählen. Ein "➕ Neue Düse hinzufügen"-Eintrag erlaubt das dynamische Erweitern der Slot-Liste.
- **Automatische Düsenwechsel-Erkennung:** Beim Wechsel von Düsengröße oder -typ wird automatisch eine Benachrichtigung gesendet (HA persistent + mobile push mit Slot-Buttons). Unterstützt Einzel- und Dual-Düsen-Drucker (H2D: separate Erkennung für links/rechts).
- **Per-Slot-Reset-Button:** Jeder Düsen-Slot hat einen eigenen Reset-Button zum Zurücksetzen der Betriebsstunden.
- **Sensor-Attribute für Düsen:** Alle Düsen-Stunden-Sensoren (`nozzle_hours`, `left_nozzle_hours`, `right_nozzle_hours`) zeigen nun die Stunden der aktiven Düse und liefern Attribute mit einer Übersicht aller Slots (`alle_düsen: {"Düse 1": 45.2h, ...}`).

### Fixed
- **Druckzeit gesamt wird nicht mehr auf 0 zurückgesetzt:** Beim Drucker-Ausschalten bleibt der `bambu_total_hours`-Wert nun erhalten statt auf 0 zu fallen. Der Coordinator speichert den letzten bekannten Wert und übernimmt nur echte Updates > 0.
- Benachrichtigung "Bambu Companion – Karten bereit" entfernt (User-Request).

### Changed
- **Sensor-Einheit "prints" → "Drucke":** Alle Druckzähler-Sensoren (`total_prints`, `successful_prints`, `failed_prints`, `monthly_prints`) zeigen nun die deutsche Einheit "Drucke" statt "prints".
- **Icons für Kostensensoren:** `last_print_cost` und `total_filament_cost` nutzen jetzt beide `mdi:currency-eur` (vorher: `mdi:receipt` / `mdi:spool`).
- **HA-Benachrichtigungen für Düsenwechsel konfigurierbar:** Neues Event `"nozzle_change"` in beiden Event-Selektoren (Mobile / HA). Standard: HA-Benachrichtigung aktiviert, Mobile optional.

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