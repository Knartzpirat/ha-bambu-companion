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

_ADD_NOZZLE_OPTION = "➕ Neue Düse hinzufügen"


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
    features = coordinator._features

    entities = []

    if applicable_tasks:
        entities.append(BcMaintenanceTaskSelect(coordinator, entry, serial, applicable_tasks))

    # Nozzle slot selects
    if features.get("dual_nozzle"):
        entities.append(BcNozzleSelect(coordinator, entry, serial, "left", "Aktive Düse (Links)"))
        entities.append(BcNozzleSelect(coordinator, entry, serial, "right", "Aktive Düse (Rechts)"))
    else:
        entities.append(BcNozzleSelect(coordinator, entry, serial, "single", "Aktive Düse"))

    if entities:
        async_add_entities(entities)


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


class BcNozzleSelect(SelectEntity):
    """Dropdown to pick the active physical nozzle slot (dynamically expandable)."""

    def __init__(
        self,
        coordinator: BambuPrintTrackerCoordinator,
        entry: ConfigEntry,
        serial: str,
        position: str,
        name: str,
    ) -> None:
        self._coordinator = coordinator
        self._serial = serial
        self._position = position
        self._attr_name = name
        self._attr_unique_id = f"bc_{serial}_nozzle_select_{position}"
        self.entity_id = f"select.bc_{serial.lower()}_nozzle_{position}"
        self._attr_icon = "mdi:printer-3d-nozzle"
        self._attr_device_info = device_info(entry, serial)

    @property
    def options(self) -> list[str]:
        labels = self._coordinator.get_nozzle_slot_labels(self._position)
        return labels + [_ADD_NOZZLE_OPTION]

    @property
    def current_option(self) -> str | None:
        return self._coordinator.get_active_nozzle_label(self._position)

    async def async_select_option(self, option: str) -> None:
        if option == _ADD_NOZZLE_OPTION:
            await self._coordinator.async_add_nozzle_slot(self._position)
        else:
            await self._coordinator.async_select_nozzle_slot(self._position, option)
        self.async_write_ha_state()
