"""Dashboard generator for Bambu Companion – writes directly into HA Lovelace storage."""
from __future__ import annotations

import uuid

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .maintenance import get_applicable_tasks

_LOVELACE_DASHBOARDS_KEY = "lovelace.dashboards"
_LOVELACE_DASHBOARDS_VERSION = 1
_LOVELACE_CONFIG_VERSION = 1


async def async_setup_lovelace_dashboard(
    hass: HomeAssistant,
    serial: str,
    model: str,
    has_ams: bool,
    printer_name: str,
    currency: str = "€",
) -> str:
    """Create or update the Bambu Companion dashboard in HA Lovelace storage.

    After HA restarts the dashboard appears automatically in the sidebar.
    """
    url_path = f"bambu-companion-{serial}"
    dashboard_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, url_path))
    tasks = get_applicable_tasks(model, has_ams)

    lovelace_config = {
        "views": [
            {
                "title": "Übersicht",
                "path": "uebersicht",
                "icon": "mdi:view-dashboard",
                "cards": [_overview_card(serial, printer_name, currency, has_ams)],
            },
            {
                "title": "Wartung",
                "path": "wartung",
                "icon": "mdi:wrench-clock",
                "cards": [_maintenance_card(serial, tasks)],
            },
            {
                "title": "Historie",
                "path": "historie",
                "icon": "mdi:history",
                "cards": [_history_card(serial, currency)],
            },
        ]
    }

    # Write dashboard config into HA storage
    config_store = Store(hass, _LOVELACE_CONFIG_VERSION, f"lovelace.{url_path}")
    await config_store.async_save({"config": lovelace_config})

    # Register dashboard in the global lovelace dashboards list
    dashboards_store = Store(hass, _LOVELACE_DASHBOARDS_VERSION, _LOVELACE_DASHBOARDS_KEY)
    stored = await dashboards_store.async_load() or {}
    items: list = stored.get("items", [])
    items = [i for i in items if i.get("url_path") != url_path]  # remove stale entry
    items.append(
        {
            "icon": "mdi:printer-3d",
            "id": dashboard_id,
            "mode": "storage",
            "require_admin": False,
            "show_in_sidebar": True,
            "title": f"🖨️ {printer_name}",
            "url_path": url_path,
        }
    )
    await dashboards_store.async_save({"items": items})

    return url_path


async def async_remove_lovelace_dashboard(hass: HomeAssistant, serial: str) -> None:
    """Remove the dashboard from HA Lovelace storage on integration removal."""
    url_path = f"bambu-companion-{serial}"

    config_store = Store(hass, _LOVELACE_CONFIG_VERSION, f"lovelace.{url_path}")
    await config_store.async_remove()

    dashboards_store = Store(hass, _LOVELACE_DASHBOARDS_VERSION, _LOVELACE_DASHBOARDS_KEY)
    stored = await dashboards_store.async_load() or {}
    items = [i for i in stored.get("items", []) if i.get("url_path") != url_path]
    await dashboards_store.async_save({"items": items})


# ---------------------------------------------------------------------------
# Card builders
# ---------------------------------------------------------------------------

def _overview_card(serial: str, printer_name: str, currency: str, has_ams: bool) -> dict:
    s = serial
    rows = [
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
    if has_ams:
        rows += [
            {"type": "divider"},
            {"entity": f"sensor.bpt_{s}_ams_warning", "name": "AMS Filament-Warnung"},
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
