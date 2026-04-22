"""Bambu Print Tracker – Home Assistant Custom Integration."""
from __future__ import annotations

import logging

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
from .dashboard import async_setup_lovelace_dashboard, async_remove_lovelace_dashboard

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

    await _setup_dashboard(hass, entry)

    return True


async def _setup_dashboard(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Write dashboard into HA Lovelace storage and notify the user once."""
    opts = {**entry.data, **entry.options}
    serial: str = entry.data.get("serial", "unknown")
    model: str = entry.data.get("model", "")
    has_ams: bool = bool(entry.data.get("ams_device_ids", []))
    printer_name: str = opts.get(CONF_PRINTER_DISPLAY_NAME, DEFAULT_PRINTER_NAME)
    currency: str = opts.get(CONF_CURRENCY, DEFAULT_CURRENCY)

    try:
        url_path = await async_setup_lovelace_dashboard(
            hass, serial, model, has_ams, printer_name, currency
        )
        _LOGGER.info("Bambu Companion: Lovelace dashboard written to storage (/%s)", url_path)

        async_create(
            hass,
            (
                f"Das **{printer_name}** Dashboard wurde automatisch angelegt.\n\n"
                "Starte Home Assistant einmal neu – danach erscheint es mit 3 Reiter "
                "(**Übersicht · Wartung · Historie**) automatisch in der Seitenleiste. "
                "Kein Kopieren, kein Einfügen."
            ),
            title="Bambu Companion – Dashboard bereit",
            notification_id=f"bambu_companion_dashboard_{serial}",
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Bambu Companion: Could not write Lovelace dashboard: %s", err)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up Lovelace dashboard when integration is removed."""
    serial: str = entry.data.get("serial", "unknown")
    try:
        await async_remove_lovelace_dashboard(hass, serial)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Bambu Companion: Could not remove Lovelace dashboard: %s", err)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)



async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
