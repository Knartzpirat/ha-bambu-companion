"""Dashboard YAML generator for Bambu Print Tracker."""
from __future__ import annotations

import yaml

from .const import MAINTENANCE_TASKS
from .maintenance import get_applicable_tasks


def generate_dashboard(
    serial: str,
    model: str,
    has_ams: bool,
    printer_name: str,
    currency: str = "€",
) -> str:
    """Generate a Lovelace dashboard YAML string."""

    applicable_tasks = get_applicable_tasks(model, has_ams)

    views = [
        {
            "title": f"{printer_name} – Tracker",
            "path": f"bambu-tracker-{serial}",
            "cards": [
                _stat_card(serial, printer_name, currency),
                _maintenance_card(serial, applicable_tasks),
                _history_card(),
            ],
        }
    ]

    if has_ams:
        views[0]["cards"].append(_ams_card(serial))

    return yaml.dump({"views": views}, allow_unicode=True, default_flow_style=False)


def _stat_card(serial: str, printer_name: str, currency: str) -> dict:
    return {
        "type": "vertical-stack",
        "cards": [
            {"type": "markdown", "content": f"## 📊 {printer_name} – Statistiken"},
            {
                "type": "glance",
                "title": "Gesamtstatistiken",
                "entities": [
                    {"entity": f"sensor.bpt_{serial}_total_prints", "name": "Drucke"},
                    {"entity": f"sensor.bpt_{serial}_successful_prints", "name": "Erfolgreich"},
                    {"entity": f"sensor.bpt_{serial}_failed_prints", "name": "Fehler"},
                    {"entity": f"sensor.bpt_{serial}_total_print_time", "name": "Druckzeit"},
                    {"entity": f"sensor.bpt_{serial}_total_energy", "name": "Energie"},
                    {"entity": f"sensor.bpt_{serial}_total_cost", "name": f"Kosten ({currency})"},
                ],
            },
            {
                "type": "glance",
                "title": "Dieser Monat",
                "entities": [
                    {"entity": f"sensor.bpt_{serial}_monthly_prints", "name": "Drucke"},
                    {"entity": f"sensor.bpt_{serial}_monthly_cost", "name": f"Kosten ({currency})"},
                ],
            },
        ],
    }


def _maintenance_card(serial: str, tasks: list[dict]) -> dict:
    entity_rows = []
    for task in tasks:
        entity_rows.append(
            {
                "type": "button",
                "entity": f"button.bpt_{serial}_reset_maint_{task['key']}",
                "name": f"Reset: {task['name']}",
                "show_state": False,
            }
        )
        entity_rows.append(
            {
                "entity": f"sensor.bpt_{serial}_maint_{task['key']}",
                "name": task["name"],
            }
        )

    return {
        "type": "vertical-stack",
        "cards": [
            {"type": "markdown", "content": "## 🔧 Wartungsplan"},
            {
                "type": "entities",
                "title": "Wartungsaufgaben",
                "entities": entity_rows,
            },
        ],
    }


def _history_card() -> dict:
    return {
        "type": "markdown",
        "content": (
            "## 📋 Druckhistorie\n\n"
            "> Letzte Drucke sind im `bambu_companion` Sensor-Attribut `history` verfügbar. "
            "Für eine tabellarische Ansicht wird `flex-table-card` (HACS) empfohlen."
        ),
    }


def _ams_card(serial: str) -> dict:
    return {
        "type": "vertical-stack",
        "cards": [
            {"type": "markdown", "content": "## 🧵 Filament-Status"},
            {
                "type": "entity",
                "entity": f"sensor.bpt_{serial}_ams_warning",
                "name": "AMS Filament-Warnung",
            },
        ],
    }
