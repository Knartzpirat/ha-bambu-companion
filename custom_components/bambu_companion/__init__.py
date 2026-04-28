"""Bambu Print Tracker – Home Assistant Custom Integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CURRENCY,
    CONF_PRINTER_DISPLAY_NAME,
    DEFAULT_CURRENCY,
    DEFAULT_PRINTER_NAME,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import BambuPrintTrackerCoordinator
from .frontend import BambuCompanionCardRegistration

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

    # Register JS cards once per HA session (idempotent)
    if "card_registration" not in hass.data[DOMAIN]:
        registration = BambuCompanionCardRegistration(hass)
        await registration.async_register()
        hass.data[DOMAIN]["card_registration"] = registration

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Unregister JS cards when no more entries remain
        remaining = [k for k in hass.data[DOMAIN] if k != "card_registration"]
        if not remaining:
            registration = hass.data[DOMAIN].pop("card_registration", None)
            if registration:
                await registration.async_unregister()
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up when integration is removed."""
    pass


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
