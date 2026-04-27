"""Select entities for Bambu Print Tracker."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
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
    applicable_tasks = get_applicable_tasks(model, has_ams)

    if applicable_tasks:
        async_add_entities([
            BcMaintenanceTaskSelect(coordinator, entry, serial, applicable_tasks)
        ])


class BcMaintenanceTaskSelect(RestoreEntity, SelectEntity):
    """Dropdown to pick which maintenance task to reset."""

    def __init__(
        self,
        coordinator: BambuPrintTrackerCoordinator,
        entry: ConfigEntry,
        serial: str,
        tasks: list[dict],
    ) -> None:
        self._coordinator = coordinator
        self._serial = serial
        self._tasks = tasks
        self._attr_options = [t["name"] for t in tasks]
        self._attr_current_option = tasks[0]["name"] if tasks else None
        self._attr_has_entity_name = True
        self._attr_translation_key = "maintenance_task_select"
        self._attr_unique_id = f"bc_{serial}_select_maintenance_task"
        self.entity_id = f"select.bc_{serial.lower()}_maintenance_task"
        self._attr_icon = "mdi:wrench-cog"
        self._attr_device_info = device_info(entry, serial)

    async def async_added_to_hass(self) -> None:
        """Restore last selected option after HA restart."""
        last_state = await self.async_get_last_state()
        if last_state and last_state.state in self._attr_options:
            self._attr_current_option = last_state.state

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
