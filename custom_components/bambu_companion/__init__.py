"""Bambu Print Tracker – Home Assistant Custom Integration."""
from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
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

    # Register dashboard download service (once per domain)
    if not hass.services.has_service(DOMAIN, "download_dashboard"):
        async def _handle_download_dashboard(call: ServiceCall) -> None:
            """Write dashboard YAML to /config/www/ and notify the user."""
            opts = {**entry.data, **entry.options}
            serial: str = entry.data.get("serial", "unknown")
            model: str = entry.data.get("model", "")
            has_ams: bool = bool(entry.data.get("ams_device_ids", []))
            printer_name: str = opts.get(CONF_PRINTER_DISPLAY_NAME, DEFAULT_PRINTER_NAME)
            currency: str = opts.get(CONF_CURRENCY, DEFAULT_CURRENCY)

            yaml_content = generate_dashboard(serial, model, has_ams, printer_name, currency)

            www_path = hass.config.path("www")
            os.makedirs(www_path, exist_ok=True)
            filename = f"bambu_companion_dashboard_{serial}.yaml"
            filepath = os.path.join(www_path, filename)

            def _write() -> None:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(yaml_content)

            await hass.async_add_executor_job(_write)

            async_create(
                hass,
                (
                    f"Das Bambu Companion Dashboard wurde gespeichert:\n\n"
                    f"`/config/www/{filename}`\n\n"
                    "Du kannst den Inhalt der Datei direkt als neues Lovelace-Dashboard "
                    "einfügen (**Einstellungen → Dashboards → Dashboard hinzufügen → YAML-Modus**)."
                ),
                title="Bambu Companion – Dashboard generiert",
                notification_id=f"bambu_companion_dashboard_{serial}",
            )
            _LOGGER.info("Dashboard YAML written to %s", filepath)

        hass.services.async_register(DOMAIN, "download_dashboard", _handle_download_dashboard)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
