"""Entity discovery helpers for Bambu Print Tracker.

All entity lookups use unique_id patterns to avoid language-dependent entity IDs.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo

from .const import BAMBU_LAB_DOMAIN, DOMAIN


def get_bambu_devices(hass: HomeAssistant) -> list[dict]:
    """Return all bambu_lab printer devices registered in HA."""
    dev_reg = dr.async_get(hass)
    bambu_devices = []

    for device in dev_reg.devices.values():
        for config_entry_id in device.config_entries:
            config_entry = hass.config_entries.async_get_entry(config_entry_id)
            if config_entry and config_entry.domain == BAMBU_LAB_DOMAIN:
                serial = _extract_serial(device)
                bambu_devices.append(
                    {
                        "device_id": device.id,
                        "name": device.name_by_user or device.name or "Unknown",
                        "model": _normalize_model(device.model or ""),
                        "serial": serial,
                    }
                )
                break  # one config entry match is enough

    return bambu_devices


def _extract_serial(device: dr.DeviceEntry) -> str:
    """Extract serial number from device identifiers."""
    for domain, identifier in device.identifiers:
        if domain == BAMBU_LAB_DOMAIN:
            return identifier
    # Fallback: return first identifier if bambu_lab domain not found
    for _domain, identifier in device.identifiers:
        return identifier
    return ""


def _normalize_model(model: str) -> str:
    """Normalize model string to key used in PRINTER_FEATURES."""
    model_upper = model.upper().replace(" ", "").replace("-", "")
    mapping = {
        "X1CARBON": "X1C",
        "X1C": "X1C",
        "X1E": "X1E",
        "X1": "X1",
        "P1P": "P1P",
        "P1S": "P1S",
        "P2S": "P2S",
        "A1MINI": "A1MINI",
        "A1": "A1",
        "H2D": "H2D",
        "H2C": "H2C",
    }
    # Longest match first (e.g. A1MINI before A1)
    for key in sorted(mapping, key=len, reverse=True):
        if model_upper.startswith(key):
            return mapping[key]
    return model_upper


def get_ams_devices(hass: HomeAssistant, printer_device_id: str) -> list[dict]:
    """Return AMS sub-devices for a given printer device."""
    dev_reg = dr.async_get(hass)
    ams_devices = []

    for device in dev_reg.devices.values():
        if device.via_device_id != printer_device_id:
            continue
        model = device.model or ""
        if "AMS" in model or "Spool" in model:
            ams_devices.append(
                {
                    "device_id": device.id,
                    "name": device.name_by_user or device.name or "AMS",
                    "model": model,
                }
            )

    return ams_devices


def get_printer_entities(hass: HomeAssistant, device_id: str) -> dict[str, str]:
    """Return {translation_key: entity_id} for a bambu_lab device.

    Uses the entity registry and translation_key so results are
    language-independent.
    """
    ent_reg = er.async_get(hass)
    result: dict[str, str] = {}

    for entry in er.async_entries_for_device(ent_reg, device_id):
        if entry.platform == BAMBU_LAB_DOMAIN and entry.translation_key:
            result[entry.translation_key] = entry.entity_id

    return result


def get_ams_tray_entities(hass: HomeAssistant, ams_device_id: str) -> dict[str, str]:
    """Return {translation_key: entity_id} for an AMS device."""
    return get_printer_entities(hass, ams_device_id)


def get_entity_state(hass: HomeAssistant, entities: dict[str, str], key: str):
    """Safely get state value for a translation_key."""
    entity_id = entities.get(key)
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable"):
        return None
    return state.state


def get_entity_attribute(
    hass: HomeAssistant, entities: dict[str, str], key: str, attribute: str
):
    """Safely get an attribute from an entity."""
    entity_id = entities.get(key)
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return state.attributes.get(attribute)


def get_entity_float(
    hass: HomeAssistant, entities: dict[str, str], key: str
) -> float | None:
    """Get entity state as float, or None if unavailable."""
    raw = get_entity_state(hass, entities, key)
    if raw is None:
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def device_info(entry: ConfigEntry, serial: str) -> DeviceInfo:
    """Return DeviceInfo for a Bambu Companion entry."""
    return DeviceInfo(
        identifiers={(DOMAIN, serial)},
        name=entry.data.get("printer_display_name", "Bambu Print Tracker"),
        manufacturer="Bambu Lab",
        model=entry.data.get("model", ""),
    )
