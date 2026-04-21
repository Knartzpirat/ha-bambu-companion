# Bambu Companion

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=Knartzpirat&repository=ha-bambu-companion&category=Integration" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/badge/version-0.0.1-blue.svg)](https://github.com/Knartzpirat/ha-bambu-companion/releases)
[![license](https://img.shields.io/github/license/Knartzpirat/ha-bambu-companion)](LICENSE)

> ⚠️ **Work in progress** – This integration is under active development. Expect breaking changes before v1.0.

A **HACS Custom Integration** for Home Assistant that extends the [ha-bambulab](https://github.com/greghesp/ha-bambulab) integration with print history, cost tracking, comprehensive maintenance reminders, filament warnings, and push notifications — for all Bambu Lab printer models.

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
| Print Bed | Clean with IPA, flip bed, inspect for wear |
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

Prefix: `sensor.bpt_{serial}_*`

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
| `sensor.bpt_all_total_energy` | Combined energy all printers |
| `sensor.bpt_all_total_cost` | Combined costs all printers |
| `sensor.bpt_all_monthly_cost` | Monthly combined costs |
| `sensor.bpt_all_active_printers` | Currently printing devices |
| `sensor.bpt_all_total_prints` | Total prints all printers |

---

### 🖨️ Supported Printer Models

| Model | Chamber Fan | Dual Nozzle | Laser | AMS Lite | Vortek |
|---|---|---|---|---|---|
| X1 / X1C | ✅ | ❌ | ❌ | ❌ | ❌ |
| X1E | ✅ | ❌ | ❌ | ❌ | ❌ |
| P1P / P1S | ❌ | ❌ | ❌ | ❌ | ❌ |
| P2S | ❌ | ❌ | ❌ | ❌ | ❌ |
| A1 / A1 Mini | ❌ | ❌ | ❌ | ✅ | ❌ |
| H2D | ✅ | ✅ | ✅ | ❌ | ❌ |
| H2C | ✅ | ❌ | ❌ | ❌ | ✅ |

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

1. Copy the contents of this repository to `config/custom_components/bambu_companion/`.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & Services**.

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
| **Kosten & Energie** | Electricity price, dynamic price sensor, smart plug sensor, filament cost, currency, unit |
| **Benachrichtigungen** | Notification targets, progress interval, quiet hours, display name |
| **Texte anpassen** | All notification titles, messages, and button labels (with variable placeholders) |
| **Wartungspläne** | Individual interval for each of the 33 maintenance tasks |
| **Allgemein** | Max history entries, low filament threshold |

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
