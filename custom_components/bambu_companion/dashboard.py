"""Dashboard generator for Bambu Companion – writes card YAML to HA config directory."""
from __future__ import annotations

import os

import yaml

from homeassistant.core import HomeAssistant

from .entity_helper import get_ams_devices, get_printer_entities
from .maintenance import get_applicable_tasks


def _yaml_file_path(hass: HomeAssistant, serial: str) -> str:
    return os.path.join(hass.config.config_dir, f"bambu_companion_{serial}.yaml")


async def async_setup_lovelace_dashboard(
    hass: HomeAssistant,
    serial: str,
    model: str,
    has_ams: bool,
    printer_name: str,
    currency: str = "€",
    ams_device_ids: list[str] | None = None,
    printer_device_id: str = "",
) -> str:
    """Write Lovelace card YAML to the HA config directory.

    The file can be included in any dashboard via the UI editor or
    ``!include bambu_companion_<serial>.yaml``.
    Returns the absolute path to the written file.
    """
    tasks = get_applicable_tasks(model, has_ams)
    ids = ams_device_ids or []
    ams_name_map = {
        d["device_id"]: d["name"]
        for d in get_ams_devices(hass, printer_device_id)
    } if printer_device_id else {}
    ams_entries = [
        (dev_id, ams_name_map.get(dev_id, f"AMS ({dev_id[:6]})"))
        for dev_id in ids
    ]
    printer_entities = get_printer_entities(hass, printer_device_id) if printer_device_id else {}
    total_usage_entity = printer_entities.get("total_usage_hours")
    cards = [
        _overview_card(serial, printer_name, currency, ams_entries, total_usage_entity),
        _maintenance_card(serial, tasks),
        _history_card(serial, currency),
    ]
    content = yaml.dump(cards, allow_unicode=True, sort_keys=False, default_flow_style=False)
    file_path = _yaml_file_path(hass, serial)
    await hass.async_add_executor_job(_write_file, file_path, content)
    return file_path


def _write_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


async def async_remove_lovelace_dashboard(hass: HomeAssistant, serial: str) -> None:
    """Remove the card YAML file when the integration is removed."""
    file_path = _yaml_file_path(hass, serial)
    await hass.async_add_executor_job(_remove_file, file_path)


def _remove_file(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Card builders
# ---------------------------------------------------------------------------

def _overview_card(serial: str, printer_name: str, currency: str, ams_entries: list[tuple[str, str]], total_usage_entity: str | None = None) -> dict:
    s = serial
    rows = []
    if total_usage_entity:
        rows.append({"entity": total_usage_entity, "name": "Gesamtnutzung Drucker"})
        rows.append({"type": "divider"})
    rows += [
        {"entity": f"sensor.bpt_{s}_print_status", "name": "Status"},
        {"entity": f"sensor.bpt_{s}_total_prints", "name": "Drucke gesamt"},
        {"entity": f"sensor.bpt_{s}_successful_prints", "name": "Erfolgreich"},
        {"entity": f"sensor.bpt_{s}_failed_prints", "name": "Fehler"},
        {"entity": f"sensor.bpt_{s}_total_print_time", "name": "Druckzeit gesamt"},
        {"entity": f"sensor.bpt_{s}_total_filament", "name": "Filament gesamt"},
        {"entity": f"sensor.bpt_{s}_total_energy", "name": "Energie gesamt"},
        {"entity": f"sensor.bpt_{s}_total_cost", "name": f"Kosten gesamt ({currency})"},
        {"type": "divider"},
        {"entity": f"sensor.bpt_{s}_monthly_prints", "name": "Drucke diesen Monat"},
        {"entity": f"sensor.bpt_{s}_monthly_cost", "name": f"Kosten diesen Monat ({currency})"},
        {"type": "divider"},
        {"entity": f"sensor.bpt_{s}_last_print_duration", "name": "Letzter Druck – Dauer"},
        {"entity": f"sensor.bpt_{s}_last_print_cost", "name": f"Letzter Druck – Kosten ({currency})"},
    ]
    return {
        "type": "entities",
        "title": f"📊 {printer_name} – Übersicht",
        "icon": "mdi:printer-3d",
        "entities": rows,
    }


def _maintenance_card(serial: str, tasks: list[dict]) -> dict:
    s = serial
    rows = []
    for task in tasks:
        rows.append(
            {
                "entity": f"sensor.bpt_{s}_maint_{task['key']}",
                "name": task["name"],
                "secondary_info": "last-changed",
            }
        )
        rows.append(
            {
                "type": "button",
                "entity": f"button.bpt_{s}_reset_maint_{task['key']}",
                "name": f"✅ Erledigt: {task['name']}",
                "show_state": False,
                "tap_action": {"action": "toggle"},
            }
        )
        rows.append({"type": "divider"})
    if rows and rows[-1].get("type") == "divider":
        rows.pop()
    return {
        "type": "entities",
        "title": "🔧 Nächste Wartungen",
        "icon": "mdi:wrench-clock",
        "entities": rows,
    }


def _history_card(serial: str, currency: str) -> dict:
    s = serial
    return {
        "type": "vertical-stack",
        "cards": [
            {
                "type": "entities",
                "title": "📋 Letzter Druck",
                "icon": "mdi:history",
                "entities": [
                    {"entity": f"sensor.bpt_{s}_print_status", "name": "Status"},
                    {"entity": f"sensor.bpt_{s}_last_print_duration", "name": "Dauer"},
                    {"entity": f"sensor.bpt_{s}_last_print_cost", "name": f"Kosten ({currency})"},
                ],
            },
            {
                "type": "markdown",
                "content": (
                    "### Vollständige Druckhistorie\n"
                    f"Die gesamte Historie steckt im Attribut `history` von\n"
                    f"`sensor.bpt_{s}_total_prints`.\n\n"
                    "Für eine Tabellendarstellung: **flex-table-card** (HACS) installieren:\n"
                    "```yaml\n"
                    "type: custom:flex-table-card\n"
                    f"entities:\n"
                    f"  include: sensor.bpt_{s}_total_prints\n"
                    "columns:\n"
                    "  - data: history[].name\n"
                    "    name: Name\n"
                    "  - data: history[].duration_min\n"
                    "    name: Dauer (min)\n"
                    "  - data: history[].cost\n"
                    "    name: Kosten\n"
                    "  - data: history[].status\n"
                    "    name: Status\n"
                    "```"
                ),
            },
        ],
    }
