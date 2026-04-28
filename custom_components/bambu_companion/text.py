"""Text entities for Bambu Print Tracker – nozzle slot renaming."""
from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BambuPrintTrackerCoordinator
from .entity_helper import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BambuPrintTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    serial = entry.data.get("serial", "unknown")
    features = coordinator._features

    entities: list[BcNozzleLabelText] = []

    if features.get("dual_nozzle"):
        entities.append(BcNozzleLabelText(coordinator, entry, serial, "left", "Düsenname (Links)"))
        entities.append(BcNozzleLabelText(coordinator, entry, serial, "right", "Düsenname (Rechts)"))
    else:
        entities.append(BcNozzleLabelText(coordinator, entry, serial, "single", "Düsenname"))

    if entities:
        async_add_entities(entities)


class BcNozzleLabelText(TextEntity):
    """Text entity to rename the currently active nozzle slot."""

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
        self._attr_unique_id = f"bc_{serial}_nozzle_label_{position}"
        self.entity_id = f"text.bc_{serial.lower()}_nozzle_label_{position}"
        self._attr_icon = "mdi:label-outline"
        self._attr_mode = TextMode.TEXT
        self._attr_native_max = 40
        self._attr_device_info = device_info(entry, serial)

    @property
    def native_value(self) -> str | None:
        """Return the label of the currently active nozzle slot."""
        return self._coordinator.get_active_nozzle_label(self._position)

    async def async_set_value(self, value: str) -> None:
        """Rename the currently active nozzle slot."""
        slots = self._coordinator._store.get_nozzle_slots(self._position)
        active_id = self._coordinator._store.get_active_nozzle_slot(self._position)
        await self._coordinator.async_rename_nozzle_slot(self._position, active_id, value)
