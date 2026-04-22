"""Bambu Print Tracker – Home Assistant Custom Integration."""
from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.persistent_notification import async_create

from .const import (
    CONF_CURRENCY,
    CONF_PRINTER_DISPLAY_NAME,
    DEFAULT_CURRENCY,
    DEFAULT_PRINTER_NAME,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import BambuPrintTrackerCoordinator
from .dashboard import generate_dashboard

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bambu Print Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = BambuPrintTrackerCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    # Auto-generate dashboard YAML into /config/www/ on every setup
    await _write_dashboard(hass, entry)

    return True


async def _write_dashboard(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Write the Lovelace dashboard YAML to /config/www/ and notify once."""
    opts = {**entry.data, **entry.options}
    serial: str = entry.data.get("serial", "unknown")
    model: str = entry.data.get("model", "")
    has_ams: bool = bool(entry.data.get("ams_device_ids", []))
    printer_name: str = opts.get(CONF_PRINTER_DISPLAY_NAME, DEFAULT_PRINTER_NAME)
    currency: str = opts.get(CONF_CURRENCY, DEFAULT_CURRENCY)

    yaml_content = generate_dashboard(serial, model, has_ams, printer_name, currency)

    www_path = hass.config.path("www")
    filename = f"bambu_companion_dashboard_{serial}.yaml"
    filepath = os.path.join(www_path, filename)

    def _write() -> None:
        os.makedirs(www_path, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(yaml_content)

    await hass.async_add_executor_job(_write)
    _LOGGER.info("Bambu Companion: Dashboard YAML written to %s", filepath)

    async_create(
        hass,
        (
            f"Das Bambu Companion Dashboard wurde automatisch erstellt:\n\n"
            f"`/config/www/{filename}`\n\n"
            "Gehe zu **Einstellungen → Dashboards → Dashboard hinzufügen**, "
            "wähle **Neues Dashboard aus YAML** und füge den Inhalt der Datei ein."
        ),
        title="Bambu Companion – Dashboard bereit",
        notification_id=f"bambu_companion_dashboard_{serial}",
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
