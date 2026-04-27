# Bambu Companion

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/badge/version-0.0.4-blue.svg)](https://github.com/Knartzpirat/ha-bambu-companion/releases)
[![license](https://img.shields.io/github/license/Knartzpirat/ha-bambu-companion)](LICENSE)

> ⚠️ **Work in progress** – This integration is under active development. Expect breaking changes before v1.0.

A **HACS Custom Integration** for Home Assistant that extends [ha-bambulab](https://github.com/greghesp/ha-bambulab) with print history, cost tracking, maintenance reminders, and push notifications — for all supported Bambu Lab printer models.

Bambu Companion **never communicates directly with the printer**. It reads exclusively from ha-bambulab entities. Entity discovery is always language-safe — entity IDs are never hardcoded.

---

## Requirements

1. **[ha-bambulab](https://github.com/greghesp/ha-bambulab)** (v2.2.21+) installed with at least one printer configured.
2. **HACS** installed in your Home Assistant instance.
3. A **mobile notification service** (`notify.*`) for push notifications (optional).

---

## Features

### 🔔 Push Notifications

Fully customizable templates using variables such as `{drucker}`, `{name}`, `{progress}`, `{remaining}`, `{duration}`, `{weight}`, `{energy}`, `{cost}`.

| Event | When triggered |
|---|---|
| **Print started** | When a print job begins |
| **Progress update** | During printing, at a configurable interval (default: every 5 %) |
| **Print complete** | On successful finish — includes duration, filament, energy, costs |
| **Print failed** | When a print is aborted or fails |
| **Maintenance due** | When a maintenance threshold is reached (1-hour cooldown) |

**Channels:**
- **Mobile** (`notify.*` services): send to any number of targets simultaneously
- **HA persistent notifications**: shown in the Home Assistant notification panel

**Quiet hours**: Mobile notifications can be suppressed during a configurable time window. Events can be configured independently per channel via the Options Flow.

---

### 💰 Cost & Energy Tracking

- **Filament cost**: calculated from print weight (grams) and a configurable price per kg.
- **Energy cost**: integrates with a smart plug kWh sensor for real measurements. Supports static pricing and dynamic price sensors (e.g. Tibber, aWATTar).
- **Fallback**: if no energy sensor is configured, a rough 100 W estimate is used (clearly noted in logs).
- **Per-print breakdown**: filament cost + energy cost + total cost stored per print.
- **Cumulative counters**: total energy (kWh), total filament (g), total cost, filament cost, energy cost.
- **Monthly summary**: prints and costs for the current calendar month.

---

### 📋 Print History

Stores completed prints persistently in HA storage. Default: unlimited (configurable via Options → General).

Each record includes:

| Field | Description |
|---|---|
| `name` | Print job name |
| `status` | `success` / `failed` |
| `duration_min` | Duration in minutes |
| `filament_weight_g` | Filament used in grams |
| `active_tray` | Filament slot snapshot: name, color, type, AMS slot |
| `energy_kwh` | Energy consumed (measured or estimated) |
| `filament_cost` / `energy_cost` / `total_cost` | Cost breakdown |
| `nozzle_diameter` / `nozzle_type` | Nozzle details |
| `bed_type` | Print bed surface |
| `avg_bed_temp` / `avg_nozzle_temp` | Temperatures at print end |
| `layer_count` / `current_layer` | Layer data |
| `gcode_file` | G-code filename (full path as reported by ha-bambulab) |
| `project_name` | Project name extracted from the file path (e.g. `MyModel`) |
| `plate` | Plate label extracted from the file path (e.g. `Plate 2`) |
| `cover_image_entity` | Entity ID of the cover image from ha-bambulab |

---

### 🔧 Maintenance Plans

**29 maintenance tasks** covering all supported Bambu Lab printer models. Tasks are automatically filtered to match your specific printer and installed accessories.

| Category | Examples |
|---|---|
| Nozzle & Hotend | Clean/replace nozzle (single & dual), PTFE tube, heatbreak |
| Motion | Y/Z linear rails, Z lead screws, belt tension, carbon rods, extruder gear |
| Print Bed | Clean bed |
| Fans & Filters | All fans, HEPA filter, activated carbon filter |
| AMS | Purge wiper, AMS gears/rollers |
| Calibration | Resonance compensation, flow calibration |
| Laser (H2D) | Lens & fan, deep clean, laser bed, safety glass |
| H2C Vortek | Rack guide lubrication, hotend slot wear check |

**Trigger types**: print hours · total machine hours · print count · laser hours · laser jobs · nozzle hours

Each task provides:
- A **sensor** showing `ok` / `warning` with current value and configured interval as attributes
- A **reset button** that zeroes the counter with baseline tracking
- A **push notification** when the threshold is exceeded (1-hour cooldown per task)
- An individually configurable interval via Options → Maintenance Plans

---

### 📊 Sensors Created

Prefix: `sensor.bc_{serial}_*`

| Sensor | Description |
|---|---|
| `print_status` | Current print status mirrored from ha-bambulab |
| `total_prints` / `successful_prints` / `failed_prints` | Print counts |
| `total_print_time` | Total print time in hours (prefers ha-bambulab `total_usage_hours`) |
| `total_energy` | Total energy consumed (kWh) |
| `total_filament` | Total filament used (g) |
| `total_cost` / `total_filament_cost` / `total_energy_cost` | Cumulative costs |
| `monthly_cost` / `monthly_prints` | Current calendar month stats |
| `last_print_duration` / `last_print_cost` | Last print stats |
| `nozzle_hours` | Nozzle operating hours (single-nozzle printers) |
| `left_nozzle_hours` / `right_nozzle_hours` | Dual-nozzle (H2D only) |
| `laser_hours` | Laser operating hours (H2D only) |
| `maint_{task_key}` | Per maintenance task: `ok` / `warning` |

The `total_prints` sensor carries the full print history as an attribute (`history`).

---

### 🖨️ Supported Printer Models

| Model | Chamber Fan | Dual Nozzle | Laser | AMS Lite | Vortek |
|---|---|---|---|---|---|
| X1 / X1C *(Untested)* | ✅ | ❌ | ❌ | ❌ | ❌ |
| X1E *(Untested)* | ✅ | ❌ | ❌ | ❌ | ❌ |
| P1P / P1S *(Untested)* | ❌ | ❌ | ❌ | ❌ | ❌ |
| P2S *(Untested)* | ❌ | ❌ | ❌ | ❌ | ❌ |
| A1 / A1 Mini *(Untested)* | ❌ | ❌ | ❌ | ✅ | ❌ |
| H2D | ✅ | ✅ | ✅ | ❌ | ❌ |
| H2C *(Untested)* | ✅ | ❌ | ❌ | ❌ | ✅ |

---

### 🃏 Custom Lovelace Cards

Bambu Companion includes three custom Lovelace cards (automatically registered via the frontend):

- **Bambu Companion – Overview**: print statistics, cumulative totals, energy usage
- **Bambu Companion – Maintenance**: maintenance status indicators with reset buttons
- **Bambu Companion – Print History**: table of recent prints

After installation, open any dashboard in edit mode, click **Add card**, and search for **Bambu Companion**.

---

## Installation

### Via HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories.
2. Add `https://github.com/Knartzpirat/ha-bambu-companion` as type **Integration**.
3. Search for **Bambu Companion** and install.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration** → search for **Bambu Companion**.

### Manual

1. Download the latest release or clone this repository.
2. Copy the folder `custom_components/bambu_companion/` into your HA config directory: `config/custom_components/bambu_companion/`.
3. Restart Home Assistant.
4. Add the integration via **Settings → Devices & Services**.

---

## Setup

The setup wizard guides you through 4 steps:

1. **Select printer** – choose from all Bambu Lab printers detected via ha-bambulab.
2. **AMS units** – select which AMS units to monitor (auto-detected).
3. **Energy & costs** – electricity price, smart plug sensor, filament cost per kg, currency.
4. **Notifications** – notification targets, progress interval, quiet hours, display name, events per channel.

---

## Options (after setup)

Navigate to **Settings → Integrations → Bambu Companion → Configure**.

| Tab | Settings |
|---|---|
| **Costs & Energy** | Electricity price, dynamic price sensor, smart plug sensor, filament cost per kg, currency, display unit |
| **Notifications** | Notification targets, progress interval, quiet hours, display name, events per channel |
| **Customize Texts** | All notification titles, messages, and button labels (with variable placeholders) |
| **Maintenance Plans** | Individual interval for each of the 29 maintenance tasks |
| **General** | Max history entries (0 = unlimited) |

---

## Project Structure

```
custom_components/bambu_companion/
├── __init__.py          # Integration setup, card registration
├── coordinator.py       # DataUpdateCoordinator, state machine, core logic
├── sensor.py            # Stat and maintenance sensors
├── button.py            # Maintenance reset buttons
├── config_flow.py       # Setup wizard (4 steps)
├── options_flow.py      # Options tabs (5 tabs)
├── storage.py           # JSON persistence via HA Store
├── notify.py            # Notification manager
├── entity_helper.py     # ha-bambulab device/entity discovery helpers
├── maintenance.py       # Maintenance task filtering and formatting
├── const.py             # All constants, MAINTENANCE_TASKS, PRINTER_FEATURES
├── manifest.json
├── strings.json
├── frontend/
│   ├── __init__.py      # JS card registration
│   └── bambu-companion-cards.js
└── translations/
    ├── de.json
    └── en.json
```

---

## Known Limitations

- Firmware lockdown (X1C FW 01.08.05.00+ / P1 FW 01.07.00.00+ / A1 FW 01.05.00.00+): write controls only work in Developer LAN Mode. Read-only sensors always work.
- Energy measurement requires an external smart plug with a kWh sensor. Without it, a flat 100 W estimate is used.
- Print history is stored per-printer. There are no cross-printer aggregate sensors.

---

## Contributing

Bug reports and feature requests are welcome — please open an issue in this repository.

---

## Credits

Inspired by [ha-bambu-print-tracker](https://github.com/willhaggan/ha-bambu-print-tracker) by [@willhaggan](https://github.com/willhaggan). 🙏

Built on top of [ha-bambulab](https://github.com/greghesp/ha-bambulab) by [@greghesp](https://github.com/greghesp).


---

## Features

### 🔔 Push Notifications

All notifications use fully customizable templates with variables like `{drucker}`, `{name}`, `{progress}`, `{remaining}`, `{duration}`, `{weight}`, `{energy}`, `{cost}`.

| Notification | When |
|---|---|
| **Progress update** | During printing, at a configurable interval (default: every 5 %) |
| **Print complete** | When a print finishes successfully — incl. duration, filament, energy, costs |
| **Print failed** | When a print is aborted or fails |
| **Maintenance due** | When a maintenance threshold is reached |
| **Reset confirmation** | When a reset button is pressed |

- **Quiet hours**: Progress notifications are suppressed during configurable time windows. Completion and failure alerts always go through.
- **Multiple targets**: Send to any number of `notify.*` services simultaneously.

---

### 💰 Cost & Energy Tracking

- **Filament cost**: Calculated from print weight and a configurable price per kg, display unit selectable (kg / g).
- **Energy cost**: Integrates with a smart plug kWh sensor. Supports static pricing and dynamic price sensors (e.g. Tibber, aWATTar).
- **Per-print breakdown**: Filament cost + energy cost + total cost stored per print.
- **Cumulative counters**: Total energy (kWh), total cost, total filament (g) across all prints.
- **Monthly summary**: Prints and costs for the current calendar month.

---

### 📋 Print History

Stores the last **N prints** (default 50, configurable 10–500) persistently in HA storage.

Each record includes:

| Field | Description |
|---|---|
| `name` | Print job name |
| `status` | `success` / `failed` |
| `duration_min` | Duration in minutes |
| `filament_weight_g` | Filament used in grams |
| `filament_types` / `filament_colors` | Materials and colors from AMS |
| `energy_kwh` | Energy consumed |
| `filament_cost` / `energy_cost` / `total_cost` | Cost breakdown |
| `nozzle_size` / `nozzle_type` | Nozzle details |
| `bed_type` | Print bed surface |
| `avg_bed_temp` / `avg_nozzle_temp` | Average temperatures |
| `layer_count` / `current_layer` | Layer data |

---

### 🔧 Maintenance Plans

**33 maintenance tasks** covering all Bambu Lab printer models. Tasks are automatically filtered to match your specific printer.

| Category | Examples |
|---|---|
| Nozzle & Hotend | Clean/replace nozzle, PTFE tube, heatbreak |
| Motion | X/Y rail lubrication, Z axis, belt tension, carbon rods |
| Print Bed | Clean bed, flip bed, inspect for wear |
| Fans & Filters | Part cooling fan, HEPA filter, activated carbon filter |
| AMS | Purge wiper, cutter blade, gear cleaning |
| Calibration | Resonance, flow, first-layer calibration |
| Laser (H2D) | Lens, air nozzle, laser bed, safety glass |
| H2C Vortek Rack | Rack guide lubrication, hotend slot wear |

**Trigger types**: print hours · total hours · print count · laser hours · nozzle hours

Each task has:
- A **sensor** showing `ok` / `warning` with current value and configured interval
- A **reset button** that zeroes the counter (with baseline tracking)
- A **push notification** when the threshold is exceeded (with 1-hour cooldown)
- Individually configurable intervals via the Options Flow

---

### 🧵 Filament (AMS) Warnings

- Monitors all configured AMS units and trays.
- Sensor state: `ok` / `low` / `empty` per AMS device.
- Low threshold configurable (default: 15 %).
- Triggered by the `empty` attribute or `remaining_filament < threshold %`.

---

### 📊 Sensors Created

Prefix: `sensor.bc_{serial}_*`

| Sensor | Description |
|---|---|
| `print_status` | Current print status (mirrored + extended) |
| `total_prints` / `successful_prints` / `failed_prints` | Print counts |
| `total_print_time` | Total print time (h) |
| `total_energy` | Total energy consumed (kWh) |
| `total_filament` | Total filament used (g) |
| `total_cost` / `monthly_cost` | Costs (€ or configured currency) |
| `monthly_prints` | Prints this month |
| `last_print_duration` / `last_print_cost` | Last print stats |
| `nozzle_hours` | Nozzle operating hours |
| `left_nozzle_hours` / `right_nozzle_hours` | Dual-nozzle (H2D) |
| `laser_hours` | Laser operating hours (H2D) |
| `maint_{task_key}` | Per maintenance task: `ok` / `warning` |

**Multi-printer aggregation** (when more than one printer is configured):

| Sensor | Description |
|---|---|
| `sensor.bc_all_total_energy` | Combined energy all printers |
| `sensor.bc_all_total_cost` | Combined costs all printers |
| `sensor.bc_all_monthly_cost` | Monthly combined costs |
| `sensor.bc_all_active_printers` | Currently printing devices |
| `sensor.bc_all_total_prints` | Total prints all printers |

---

### 🖨️ Supported Printer Models

| Model | Chamber Fan | Dual Nozzle | Laser | AMS Lite | Vortek |
|---|---|---|---|---|---|
| X1 / X1C *(Untested)* | ✅ | ❌ | ❌ | ❌ | ❌ |
| X1E *(Untested)* | ✅ | ❌ | ❌ | ❌ | ❌ |
| P1P / P1S *(Untested)* | ❌ | ❌ | ❌ | ❌ | ❌ |
| P2S *(Untested)* | ❌ | ❌ | ❌ | ❌ | ❌ |
| A1 / A1 Mini *(Untested)* | ❌ | ❌ | ❌ | ✅ | ❌ |
| H2D | ✅ | ✅ | ✅ | ❌ | ❌ |
| H2C *(Untested)* | ✅ | ❌ | ❌ | ❌ | ✅ |

---

## Requirements

1. **[ha-bambulab](https://github.com/greghesp/ha-bambulab)** (v2.2.21+) installed and at least one printer configured.
2. **HACS** installed in your Home Assistant instance.
3. A **mobile notification service** (`notify.*`) for push notifications (optional but recommended).

> ⚠️ **Important**: Bambu Companion **never communicates directly with the printer**. It reads exclusively from ha-bambulab entities. Entity discovery is always language-safe — entity IDs are never hardcoded.

> ⚠️ **Firmware Lockdown**: From X1C FW 01.08.05.00 / P1 FW 01.07.00.00 / A1 FW 01.05.00.00, write controls only work in Developer LAN Mode. Read-only sensors always work.

---

## Installation

### Via HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories.
2. Add `https://github.com/Knartzpirat/ha-bambu-companion` as type **Integration**.
3. Search for **Bambu Companion** and install.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration** → search for **Bambu Companion**.

### Manual

1. Download the latest release or clone this repository.
2. Copy the folder `custom_components/bambu_print_tracker/` into your HA config directory so the result is `config/custom_components/bambu_print_tracker/`.
3. Restart Home Assistant.
4. Add the integration via **Settings → Devices & Services**.

---

## Setup

The setup wizard guides you through 4 steps:

1. **Select printer** – choose from all Bambu Lab printers detected via ha-bambulab.
2. **AMS units** – select which AMS units to monitor (auto-detected).
3. **Energy & costs** – electricity price, smart plug sensor, filament cost, currency.
4. **Notifications** – notification targets, progress interval, quiet hours, display name.

All settings can be changed later via **Settings → Integrations → Bambu Companion → Configure**.

---

## Options (after setup)

| Tab | Settings |
|---|---|
| **Costs & Energy** | Electricity price, dynamic price sensor, smart plug sensor, filament cost, currency, unit |
| **Notifications** | Notification targets, progress interval, quiet hours, display name |
| **Customize Texts** | All notification titles, messages, and button labels (with variable placeholders) |
| **Maintenance Plans** | Individual interval for each of the 29 maintenance tasks |
| **General** | Max history entries, low filament threshold |

---

## Dashboard

The integration can generate a supplementary Lovelace dashboard YAML that **adds** to the existing ha-bambulab cards:

- Statistics section (costs / energy / prints — daily, monthly, total)
- Maintenance plan with status indicators and reset buttons
- Print history table (last 10 prints)
- AMS filament level warnings

> The dashboard requires [mushroom-cards](https://github.com/piitaya/lovelace-mushroom) and [mini-graph-card](https://github.com/kalkih/mini-graph-card) (both available via HACS).

---

## Contributing

Bug reports and feature requests are welcome — please open an issue in this repository.

---

## Credits

Inspired by the original blueprint [ha-bambu-print-tracker](https://github.com/willhaggan/ha-bambu-print-tracker) by [@willhaggan](https://github.com/willhaggan). 🙏

Built on top of the excellent [ha-bambulab](https://github.com/greghesp/ha-bambulab) integration by [@greghesp](https://github.com/greghesp).
