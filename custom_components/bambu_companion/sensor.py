"""Sensors for Bambu Print Tracker."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MAINTENANCE_TASKS, PRINTER_FEATURES
from .coordinator import BambuPrintTrackerCoordinator
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
    features = PRINTER_FEATURES.get(model, {})
    currency = entry.data.get("currency", "€")

    entities: list[SensorEntity] = [
        BptStatSensor(coordinator, entry, serial, "print_status", "Druckstatus", "mdi:printer-3d-nozzle", None, None),
        BptStatSensor(coordinator, entry, serial, "total_prints", "Drucke gesamt", "mdi:printer-3d", None, "prints"),
        BptStatSensor(coordinator, entry, serial, "successful_prints", "Erfolgreiche Drucke", "mdi:check-circle", None, "prints"),
        BptStatSensor(coordinator, entry, serial, "failed_prints", "Fehlgeschlagene Drucke", "mdi:close-circle", None, "prints"),
        BptStatSensor(coordinator, entry, serial, "total_print_time", "Druckzeit gesamt", "mdi:clock-outline", SensorStateClass.TOTAL_INCREASING, UnitOfTime.HOURS),
        BptStatSensor(coordinator, entry, serial, "total_energy", "Energie gesamt", "mdi:lightning-bolt", SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR),
        BptStatSensor(coordinator, entry, serial, "total_filament", "Filament gesamt", "mdi:weight-gram", SensorStateClass.TOTAL_INCREASING, "g"),
        BptStatSensor(coordinator, entry, serial, "total_cost", "Kosten gesamt", "mdi:currency-eur", SensorStateClass.TOTAL_INCREASING, currency),
        BptStatSensor(coordinator, entry, serial, "monthly_cost", "Kosten diesen Monat", "mdi:calendar-month", None, currency),
        BptStatSensor(coordinator, entry, serial, "monthly_prints", "Drucke diesen Monat", "mdi:calendar-month", None, "prints"),
        BptStatSensor(coordinator, entry, serial, "last_print_duration", "Dauer letzter Druck", "mdi:timer-outline", None, UnitOfTime.MINUTES),
        BptStatSensor(coordinator, entry, serial, "last_print_cost", "Kosten letzter Druck", "mdi:receipt", None, currency),
    ]

    if features.get("dual_nozzle"):
        # Dual nozzle: track each nozzle separately, skip generic nozzle_hours
        entities += [
            BptStatSensor(coordinator, entry, serial, "left_nozzle_hours", "Linke Düse Betriebsstunden", "mdi:clock", SensorStateClass.TOTAL_INCREASING, UnitOfTime.HOURS),
            BptStatSensor(coordinator, entry, serial, "right_nozzle_hours", "Rechte Düse Betriebsstunden", "mdi:clock", SensorStateClass.TOTAL_INCREASING, UnitOfTime.HOURS),
        ]
    else:
        entities.append(
            BptStatSensor(coordinator, entry, serial, "nozzle_hours", "Düse Betriebsstunden", "mdi:clock", SensorStateClass.TOTAL_INCREASING, UnitOfTime.HOURS)
        )

    if features.get("laser"):
        entities.append(
            BptStatSensor(coordinator, entry, serial, "laser_hours", "Laser Betriebsstunden", "mdi:laser-pointer", SensorStateClass.TOTAL_INCREASING, UnitOfTime.HOURS)
        )

    # Maintenance sensors
    applicable_tasks = get_applicable_tasks(model, has_ams)
    for task in applicable_tasks:
        entities.append(
            BptMaintenanceSensor(coordinator, entry, serial, task)
        )

    # AMS filament warning sensors
    for idx, ams_dev_id in enumerate(entry.data.get("ams_device_ids", []), start=1):
        entities.append(
            BptAmsWarningSensor(coordinator, entry, serial, ams_dev_id, idx)
        )

    async_add_entities(entities)


def _device_info(entry: ConfigEntry, serial: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, serial)},
        name=entry.data.get("printer_display_name", "Bambu Print Tracker"),
        manufacturer="Bambu Lab (Tracker)",
        model=entry.data.get("model", ""),
    )


class BptStatSensor(CoordinatorEntity, SensorEntity):
    """Generic stat sensor for Bambu Print Tracker."""

    def __init__(
        self,
        coordinator: BambuPrintTrackerCoordinator,
        entry: ConfigEntry,
        serial: str,
        stat_key: str,
        name: str,
        icon: str | None,
        state_class,
        unit: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self._stat_key = stat_key
        self._attr_name = name
        self._attr_unique_id = f"bpt_{serial}_{stat_key}"
        self._attr_icon = icon
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = _device_info(entry, serial)

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        data = self.coordinator.data

        if self._stat_key == "print_status":
            return data.get("print_status")

        counters = data.get("counters", {})
        monthly = data.get("monthly", {})
        last = data.get("last_print") or {}

        mapping = {
            "total_prints": counters.get("total_prints", 0),
            "successful_prints": counters.get("successful_prints", 0),
            "failed_prints": counters.get("failed_prints", 0),
            "total_print_time": round(counters.get("total_print_time_min", 0) / 60, 2),
            "total_energy": round(counters.get("total_energy_kwh", 0), 3),
            "total_filament": round(counters.get("total_filament_g", 0), 1),
            "total_cost": round(counters.get("total_cost", 0), 2),
            "monthly_cost": round(monthly.get("monthly_cost", 0), 2),
            "monthly_prints": monthly.get("monthly_prints", 0),
            "last_print_duration": last.get("duration_min"),
            "last_print_cost": round(last.get("total_cost", 0), 2) if last else None,
            "nozzle_hours": round(counters.get("nozzle_hours", 0), 2),
            "left_nozzle_hours": round(counters.get("left_nozzle_hours", 0), 2),
            "right_nozzle_hours": round(counters.get("right_nozzle_hours", 0), 2),
            "laser_hours": round(counters.get("laser_hours", 0), 2),
        }
        return mapping.get(self._stat_key)


class BptMaintenanceSensor(CoordinatorEntity, SensorEntity):
    """Maintenance task sensor."""

    def __init__(
        self,
        coordinator: BambuPrintTrackerCoordinator,
        entry: ConfigEntry,
        serial: str,
        task: dict,
    ) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self._task = task
        self._attr_name = f"Wartung: {task['name']}"
        self._attr_unique_id = f"bpt_{serial}_maint_{task['key']}"
        self._attr_icon = "mdi:wrench"
        self._attr_device_info = _device_info(entry, serial)

    @property
    def native_value(self) -> str:
        if self.coordinator.data is None:
            return "ok"
        maint = self.coordinator.data.get("maintenance", {})
        key = self._task["key"]
        entry = maint.get(key, {})
        value = float(entry.get("value", 0) if isinstance(entry, dict) else entry)
        intervals = self.coordinator._options.get("maintenance_intervals", {})
        interval = float(intervals.get(key, self._task["default_interval"]))
        return "warning" if value >= interval else "ok"

    @property
    def extra_state_attributes(self) -> dict:
        if self.coordinator.data is None:
            return {}
        maint = self.coordinator.data.get("maintenance", {})
        key = self._task["key"]
        entry = maint.get(key, {})
        value = float(entry.get("value", 0) if isinstance(entry, dict) else entry)
        intervals = self.coordinator._options.get("maintenance_intervals", {})
        interval = float(intervals.get(key, self._task["default_interval"]))
        return {
            "current_value": value,
            "interval": interval,
            "trigger": self._task["trigger"],
            "task_key": key,
            "wiki_url": self._task.get("wiki"),
        }


class BptAmsWarningSensor(CoordinatorEntity, SensorEntity):
    """AMS device-level filament warning sensor."""

    def __init__(
        self,
        coordinator: BambuPrintTrackerCoordinator,
        entry: ConfigEntry,
        serial: str,
        ams_device_id: str,
        ams_index: int,
    ) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self._ams_device_id = ams_device_id
        self._ams_index = ams_index
        self._attr_name = f"AMS {ams_index} Filament-Status"
        self._attr_unique_id = f"bpt_{serial}_ams_{ams_device_id}_warning"
        self._attr_icon = "mdi:spool"
        self._attr_device_info = _device_info(entry, serial)

    @property
    def native_value(self) -> str:
        if self.coordinator.data is None:
            return "ok"
        warnings = self.coordinator.data.get("ams_warnings", {})
        statuses = [v for k, v in warnings.items() if k.startswith(self._ams_device_id)]
        if "empty" in statuses:
            return "empty"
        if "low" in statuses:
            return "low"
        return "ok"

    @property
    def extra_state_attributes(self) -> dict:
        if self.coordinator.data is None:
            return {}
        warnings = self.coordinator.data.get("ams_warnings", {})
        return {k: v for k, v in warnings.items() if k.startswith(self._ams_device_id)}
