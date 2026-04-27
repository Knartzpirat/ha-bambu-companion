"""Buttons for Bambu Print Tracker."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PRINTER_FEATURES
from .coordinator import BambuPrintTrackerCoordinator
from .entity_helper import device_info
from .maintenance import get_applicable_tasks


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BambuPrintTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    serial = entry.data.get("serial", "unknown")
    model = entry.data.get("model", "")
    has_ams = bool(entry.data.get("ams_device_ids", []))
    features = PRINTER_FEATURES.get(model, {})

    entities: list[ButtonEntity] = [
        BcResetButton(
            coordinator, entry, serial, "reset_nozzle",
            "Düsenstunden zurücksetzen", "mdi:restore",
            coordinator.async_reset_nozzle,
        ),
    ]

    if features.get("dual_nozzle"):
        entities += [
            BcResetButton(
                coordinator, entry, serial, "reset_left_nozzle",
                "Linke Düse zurücksetzen", "mdi:restore",
                coordinator.async_reset_left_nozzle,
            ),
            BcResetButton(
                coordinator, entry, serial, "reset_right_nozzle",
                "Rechte Düse zurücksetzen", "mdi:restore",
                coordinator.async_reset_right_nozzle,
            ),
        ]

    if features.get("laser"):
        entities.append(
            BcResetButton(
                coordinator, entry, serial, "reset_laser",
                "Laser-Stunden zurücksetzen", "mdi:restore",
                coordinator.async_reset_laser,
            )
        )

    # Maintenance task reset buttons
    applicable_tasks = get_applicable_tasks(model, has_ams)
    for task in applicable_tasks:
        task_key = task["key"]
        entities.append(
            BcMaintenanceResetButton(coordinator, entry, serial, task)
        )

    async_add_entities(entities)


class BcResetButton(ButtonEntity):
    """Generic reset button."""

    def __init__(
        self,
        coordinator: BambuPrintTrackerCoordinator,
        entry: ConfigEntry,
        serial: str,
        button_key: str,
        name: str,
        icon: str,
        action,
    ) -> None:
        self._coordinator = coordinator
        self._action = action
        self._attr_name = f"BC {name}"
        self._attr_unique_id = f"bc_{serial}_{button_key}"
        self.entity_id = f"button.bc_{serial.lower()}_{button_key}"
        self._attr_icon = icon
        self._attr_device_info = device_info(entry, serial)

    async def async_press(self) -> None:
        await self._action()


class BcMaintenanceResetButton(ButtonEntity):
    """Reset button for a maintenance task."""

    def __init__(
        self,
        coordinator: BambuPrintTrackerCoordinator,
        entry: ConfigEntry,
        serial: str,
        task: dict,
    ) -> None:
        self._coordinator = coordinator
        self._task_key = task["key"]
        self._attr_name = f"BC Reset: {task['name']}"
        self._attr_unique_id = f"bc_{serial}_reset_maint_{task['key']}"
        self.entity_id = f"button.bc_{serial.lower()}_reset_maint_{task['key']}"
        self._attr_icon = "mdi:restore"
        self._attr_device_info = device_info(entry, serial)

    async def async_press(self) -> None:
        await self._coordinator.async_reset_maintenance_task(self._task_key)
