# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.0.1] — 2026-05-15

### Added

**Print Tracking & History**
- Records every print with start time, duration, plate type, project name, filament source, cost and energy
- Configurable history size; data persists across HA restarts
- Print history popup card with cover image, filament source (AMS slot or external spool), bed type translation and formatted duration

**Statistics Sensors**
- Total prints, successful prints, failed prints, monthly prints
- Total print hours, total filament cost, last print cost
- Carbon filter runtime tracking (increments only for materials with fumes: ABS, ASA, PA, PC, TPU, etc.)
- Laser usage hours tracking

**Maintenance System**
- Per-task configurable maintenance plans with individual intervals and units (hours / prints / months)
- Supported tasks: nozzle, PTFE tube, filament cutter, hotend, extruder, build plate, carbon filter, first layer calibration, vibration calibration, lubrication, belt tension, camera lens, and more
- Individual enable/disable toggle per task
- "Maintenance due" notification via HA persistent notification and/or mobile push
- Reset button per maintenance task; additional select-based reset entity for automation

**Nozzle Management**
- Shared nozzle pool across all physical positions (single / left / right)
- Per-nozzle-slot hour counter with auto-increment during printing
- Add new nozzle slots dynamically; rename slots via text entity
- Active nozzle selection via dropdown; per-slot reset button
- Automatic nozzle change detection (diameter or type) with HA + mobile push notification
- Nozzle sensor attributes expose all slots and their hours

**Notifications**
- Mobile push notifications (HA Companion App) for: print started, progress, print complete, print failed, maintenance due, nozzle change
- HA persistent notifications for: print complete, print failed, maintenance due, nozzle change
- Configurable per-event enable/disable for both channels independently
- Quiet hours (from / to time): suppresses mobile push during off-hours
- Progress notification interval (every N percent)
- Mute progress notifications via action button with configurable duration (minutes)
- Three configurable notification action buttons: Bambu App deeplink, camera snapshot, mute

**Auto-Poweroff**
- Automatically switches off a configurable switch/input_boolean entity after a configurable idle time (default 60 min) with no new print
- Drying-aware modes: Ask (send notification with "Off now" / "Cancel" buttons), Always off, Wait for drying
- Timer is cancelled automatically when a new print starts

**Energy & Cost Tracking**
- Electricity price per kWh and optional external energy sensor
- Filament cost per kg with configurable unit (kg / g) and currency
- Cost calculated per print and accumulated over all time

**Frontend Cards**
- Custom Lovelace card: print history popup, live status, nozzle info, maintenance overview
- Auto-registered via `frontend/` panel; no manual resource registration required

**Options Flow**
- Tab-based settings UI: Costs & Energy, Notifications, Customize Texts, Maintenance Plans, General, Auto-Poweroff
- All settings persist via HA config entry options; survive restarts and reloads
