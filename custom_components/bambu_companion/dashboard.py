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
    cover_image_entity = printer_entities.get("cover_image")
    cards = [
        _overview_card(serial, printer_name, currency, ams_entries, total_usage_entity),
        _maintenance_card(serial, tasks),
        _history_card(serial, currency, cover_image_entity),
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


def _history_card(serial: str, currency: str, cover_image_entity: str | None = None) -> dict:
    s = serial
    entity = f"sensor.bpt_{s}_total_prints"
    cur = currency

    detail_content = (
        f"{{% set h = state_attr('{entity}', 'history') or [] %}}"
        "{% set p = h[0] if h else none %}"
        "{% if p %}"
        "{% set tray = p.active_tray or {} %}"
        "{{ '✅ Erfolgreich' if p.status == 'success' else '❌ Fehlgeschlagen' }}\n\n"
        "| | |\n"
        "|---|---|\n"
        "| 📅 Start | {{ p.timestamp_start[5:16]|replace('T',' ')|replace('-','/') if p.timestamp_start else '–' }} |\n"
        "| 🏁 Ende | {{ p.timestamp_end[5:16]|replace('T',' ')|replace('-','/') if p.timestamp_end else '–' }} |\n"
        "| ⏱️ Dauer | {% set m = p.duration_min | int %}{{ (m // 60)|string + 'h ' + (m % 60)|string + 'min' if m >= 60 else m|string + ' min' }} |\n"
        "| 🛏️ Druckbett | {{ p.bed_type or '–' }} |\n"
        "| 🔩 Düse | {{ ('%.1f mm' % (p.nozzle_diameter | float)) ~ ' – ' ~ p.nozzle_type if p.nozzle_diameter else '–' }} |\n"
        "| 🎨 Material | {{ (tray.name or '–') ~ ' (' ~ (tray.type or '–') ~ ')' }} |\n"
        "| 🎨 Farbe | {{ tray.color or '–' }} |\n"
        "| 📦 AMS-Slot | {% if tray and tray.slot is not none %}AMS {{ (tray.ams | int(0)) + 1 }} / Slot {{ (tray.slot | int(0)) + 1 }}{% else %}–{% endif %} |\n"
        "| 🧵 Filament | {{ '%.1f g' % (p.filament_weight_g | float) }} |\n"
        "| ⚡ Energie | {{ '%.3f kWh' % (p.energy_kwh | float) }} |\n"
        f"| 💡 Energiekosten | {{{{ '%.2f {cur}' % (p.energy_cost | float) }}}} |\n"
        f"| 🧵 Filamentkosten | {{{{ '%.2f {cur}' % (p.filament_cost | float) }}}} |\n"
        f"| 💵 **Gesamtkosten** | **{{{{ '%.2f {cur}' % (p.total_cost | float) }}}}** |\n"
        "| 📄 Druckdatei | {{ p.gcode_file or '–' }} |\n"
        "{% else %}"
        "_Noch kein Druck aufgezeichnet._"
        "{% endif %}"
    )

    table_content = (
        f"{{% set history = state_attr('{entity}', 'history') or [] %}}"
        "| | Name | Datum | Dauer | Filament | Kosten |\n"
        "|---|---|---|---|---|---|\n"
        "{% for p in history[:20] %}"
        "| {{ '✅' if p.status == 'success' else '❌' }} "
        "| {{ p.name or '(unbekannt)' }} "
        "| {{ p.timestamp_start[5:16]|replace('T',' ')|replace('-','/') if p.timestamp_start else '' }} "
        "| {% set m = p.duration_min | int %}{{ (m // 60)|string + 'h ' + (m % 60)|string + 'min' if m >= 60 else m|string + ' min' }} "
        "| {{ '%.1f g' % (p.filament_weight_g | float) }} "
        f"| {{{{ '%.2f {cur}' % (p.total_cost | float) }}}} |\n"
        "{% endfor %}"
        "{% if not history %}_Noch keine Drucke aufgezeichnet._{% endif %}"
    )

    cards: list[dict] = []
    if cover_image_entity:
        cards.append({
            "type": "picture-entity",
            "entity": cover_image_entity,
            "show_state": False,
            "show_name": False,
        })
    cards.extend([
        {
            "type": "markdown",
            "title": "🖨️ Letzter Druck – Details",
            "content": detail_content,
        },
        {
            "type": "markdown",
            "title": "📋 Druckverlauf (letzte 20)",
            "content": table_content,
        },
    ])
    return {
        "type": "vertical-stack",
        "cards": cards,
    }
