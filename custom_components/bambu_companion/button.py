"""Buttons for Bambu Print Tracker."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BambuPrintTrackerCoordinator
from .entity_helper import device_info
from .maintenance import get_applicable_tasks

_LOGGER = logging.getLogger(__name__)


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
        entities.append(BcResetSelectedTaskButton(coordinator, entry, serial, applicable_tasks))

    # Nozzle slot reset buttons
    if features.get("dual_nozzle"):
        entities.append(BcResetActiveNozzleButton(coordinator, entry, serial, "left", "Aktive Linke Düse zurücksetzen"))
        entities.append(BcResetActiveNozzleButton(coordinator, entry, serial, "right", "Aktive Rechte Düse zurücksetzen"))
    else:
        entities.append(BcResetActiveNozzleButton(coordinator, entry, serial, "single", "Aktive Düse zurücksetzen"))

    if entities:
        async_add_entities(entities)


class BcResetSelectedTaskButton(ButtonEntity):
    """Resets the maintenance task currently selected in the select entity."""

    def __init__(
        self,
        coordinator: BambuPrintTrackerCoordinator,
        entry: ConfigEntry,
        serial: str,
        tasks: list[dict],
    ) -> None:
        self._coordinator = coordinator
        self._serial = serial
        self._task_key_by_name: dict[str, str] = {t["name"]: t["key"] for t in tasks}
        self._attr_has_entity_name = True
        self._attr_translation_key = "reset_selected_task"
        self._attr_unique_id = f"bc_{serial}_reset_selected_task"
        self.entity_id = f"button.bc_{serial.lower()}_reset_selected_task"
        self._attr_icon = "mdi:restore"
        self._attr_device_info = device_info(entry, serial)

    async def async_press(self) -> None:
        select_entity_id = f"select.bc_{self._serial.lower()}_maintenance_task"
        state = self.hass.states.get(select_entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            _LOGGER.warning(
                "Cannot reset maintenance task: select entity %s has no valid state",
                select_entity_id,
            )
            return
        task_key = self._task_key_by_name.get(state.state)
        if task_key is None:
            _LOGGER.warning(
                "Cannot reset maintenance task: unknown task name '%s'", state.state
            )
            return
        await self._coordinator.async_reset_maintenance_task(task_key)


class BcResetActiveNozzleButton(ButtonEntity):
    """Resets the hour counter of the currently active nozzle slot."""

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
        self._attr_unique_id = f"bc_{serial}_reset_nozzle_{position}"
        self.entity_id = f"button.bc_{serial.lower()}_reset_nozzle_{position}"
        self._attr_icon = "mdi:restart"
        self._attr_device_info = device_info(entry, serial)

    async def async_press(self) -> None:
        await self._coordinator.async_reset_active_nozzle_slot(self._position)

