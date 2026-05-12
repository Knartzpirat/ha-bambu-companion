"""Bambu Print Tracker – Home Assistant Custom Integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_CURRENCY,
    CONF_NOTIFY_HA_EVENTS,
    CONF_NOTIFY_MOBILE_EVENTS,
    CONF_PRINTER_DISPLAY_NAME,
    DEFAULT_CURRENCY,
    DEFAULT_NOTIFY_HA_EVENTS,
    DEFAULT_NOTIFY_MOBILE_EVENTS,
    DEFAULT_PRINTER_NAME,
    DOMAIN,
    PLATFORMS,
    PRINTER_FEATURES,
)
from .coordinator import BambuPrintTrackerCoordinator
from .frontend import BambuCompanionCardRegistration

_LOGGER = logging.getLogger(__name__)


# All stat_keys that BcStatSensor may create (order doesn't matter)
_BASE_STAT_KEYS = [
    "print_status", "print_progress",
    "total_prints", "successful_prints", "failed_prints",
    "total_print_time", "total_energy", "total_filament", "total_cost",
    "monthly_cost", "monthly_prints",
    "last_print_duration", "last_print_cost",
    "total_filament_cost", "total_energy_cost",
]


async def _async_migrate_sensor_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate sensor entity_ids registered without the serial number.

    Older versions stored entity_ids like ``sensor.bc_print_status``.
    Current code expects ``sensor.bc_<serial>_print_status``.
    HA respects the registry, so we must update it explicitly.
    """
    serial: str = entry.data.get("serial", "")
    model: str = entry.data.get("model", "")
    if not serial:
        return

    serial_lower = serial.lower()
    features = PRINTER_FEATURES.get(model, {})

    stat_keys = list(_BASE_STAT_KEYS)
    if features.get("dual_nozzle"):
        stat_keys += ["left_nozzle_hours", "right_nozzle_hours"]
    else:
        stat_keys.append("nozzle_hours")
    if features.get("laser"):
        stat_keys.append("laser_hours")

    ent_reg = er.async_get(hass)

    for stat_key in stat_keys:
        unique_id = f"bc_{serial}_{stat_key}"
        current_entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        if not current_entity_id:
            continue
        expected_entity_id = f"sensor.bc_{serial_lower}_{stat_key}"
        if current_entity_id == expected_entity_id:
            continue
        # Ensure the target entity_id is not already occupied by a different entity
        existing = ent_reg.async_get(expected_entity_id)
        if existing and existing.unique_id != unique_id:
            _LOGGER.warning(
                "Cannot migrate %s → %s: target already used by unique_id=%s",
                current_entity_id, expected_entity_id, existing.unique_id,
            )
            continue
        _LOGGER.info("Migrating entity_id: %s → %s", current_entity_id, expected_entity_id)
        ent_reg.async_update_entity(current_entity_id, new_entity_id=expected_entity_id)


async def _async_migrate_notify_defaults(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Patch saved options that were stored before notify defaults were fixed.

    - Adds ``maintenance`` to ``notify_ha_events`` if it was missing (old default lacked it).
    - Replaces empty ``notify_mobile_events`` with the new default list.
    Only touches entries that still carry the exact old default values; explicit
    user customisations are left untouched.
    """
    options = dict(entry.options)
    changed = False

    # Patch HA events: add "maintenance" if missing and list was never customised
    ha_events: list[str] = options.get(CONF_NOTIFY_HA_EVENTS, list(DEFAULT_NOTIFY_HA_EVENTS))
    if "maintenance" not in ha_events:
        ha_events = list(ha_events) + ["maintenance"]
        options[CONF_NOTIFY_HA_EVENTS] = ha_events
        changed = True

    # Patch mobile events: if empty (old default or never set), use new default
    if CONF_NOTIFY_MOBILE_EVENTS not in options or options[CONF_NOTIFY_MOBILE_EVENTS] == []:
        options[CONF_NOTIFY_MOBILE_EVENTS] = list(DEFAULT_NOTIFY_MOBILE_EVENTS)
        changed = True

    if changed:
        _LOGGER.info(
            "Patching notify defaults for entry %s: ha_events=%s mobile_events=%s",
            entry.entry_id,
            options.get(CONF_NOTIFY_HA_EVENTS),
            options.get(CONF_NOTIFY_MOBILE_EVENTS),
        )
        hass.config_entries.async_update_entry(entry, options=options)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bambu Print Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Migrate old entity_ids before platforms are set up
    await _async_migrate_sensor_entity_ids(hass, entry)

    # Patch notification defaults for existing installs
    await _async_migrate_notify_defaults(hass, entry)

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
