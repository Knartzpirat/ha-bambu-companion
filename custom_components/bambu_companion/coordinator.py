"""DataUpdateCoordinator for Bambu Print Tracker."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ACTIVE_PRINT_STATUSES,
    CONF_AMS_DEVICE_IDS,
    CONF_CURRENCY,
    CONF_DEVICE_ID,
    CONF_ELECTRICITY_PRICE,
    CONF_ELECTRICITY_SENSOR,
    CONF_ENERGY_SENSOR,
    CONF_FILAMENT_COST,
    CONF_FILAMENT_UNIT,
    CONF_PRINTER_DISPLAY_NAME,
    DEFAULT_CURRENCY,
    DEFAULT_ELECTRICITY_PRICE,
    DEFAULT_FILAMENT_COST_PER_KG,
    DOMAIN,
    MAINTENANCE_TASKS,
    NOZZLE_ACTIVE_TEMP_THRESHOLD,
    PRINT_STATUS_FAILED,
    PRINT_STATUS_FINISH,
    PRINT_STATUS_IDLE,
    PRINT_STATUS_PRINTING,
    PRINTER_FEATURES,
    TERMINAL_PRINT_STATUSES,
)
from .entity_helper import (
    get_entity_attribute,
    get_entity_float,
    get_entity_state,
    get_printer_entities,
)
from .maintenance import get_applicable_tasks, is_maintenance_due
from .notify import NotifyManager
from .storage import PrintHistoryStore

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)


class BambuPrintTrackerCoordinator(DataUpdateCoordinator):
    """Coordinator that tracks print state for one Bambu printer."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data.get('serial', 'unknown')}",
            update_interval=UPDATE_INTERVAL,
        )
        self._entry = entry
        self._data = entry.data
        self._options = {**entry.data, **entry.options}

        self._serial: str = self._data.get("serial", "")
        self._model: str = self._data.get("model", "")
        self._device_id: str = self._data.get(CONF_DEVICE_ID, "")
        self._ams_device_ids: list[str] = self._data.get(CONF_AMS_DEVICE_IDS, [])

        self._features: dict = PRINTER_FEATURES.get(self._model, {})

        self._store = PrintHistoryStore(
            hass, self._serial, int(self._options.get("max_history", 0))
        )
        self._notify = NotifyManager(hass, self._options)

        # State machine
        self._print_status: str = PRINT_STATUS_IDLE
        self._print_start_time: datetime | None = None
        self._energy_at_start: float | None = None
        self._last_progress: int = 0
        self._last_print_name: str = ""

        # Accumulated per-session seconds for nozzle/laser tracking
        self._nozzle_session_start: datetime | None = None
        self._left_nozzle_session_start: datetime | None = None
        self._right_nozzle_session_start: datetime | None = None
        self._laser_session_start: datetime | None = None

        # Cached entity maps (populated on first refresh)
        self._entities: dict[str, str] = {}

        # Maintenance notification cooldown: task_key → last notified datetime
        self._maint_notified: dict[str, datetime] = {}

        self.data: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Setup / Teardown
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Load stored data and set up state listeners."""
        await self._store.async_load()
        self._refresh_entity_maps()
        self._setup_state_listeners()

    def _refresh_entity_maps(self) -> None:
        self._entities = get_printer_entities(self.hass, self._device_id)

    def _setup_state_listeners(self) -> None:
        """Subscribe to state changes of all tracked bambu_lab entities."""
        all_entity_ids = list(self._entities.values())

        if all_entity_ids:
            self._entry.async_on_unload(
                async_track_state_change_event(
                    self.hass,
                    all_entity_ids,
                    self._handle_state_change,
                )
            )

    @callback
    def _handle_state_change(self, event) -> None:  # noqa: ANN001
        """Trigger coordinator refresh on any tracked entity change."""
        self.hass.async_create_task(self.async_refresh())

    # ------------------------------------------------------------------
    # Core update
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        """Refresh all tracked values and run state machine."""
        # Refresh entity maps in case entities changed
        self._refresh_entity_maps()

        new_status = get_entity_state(self.hass, self._entities, "print_status") or PRINT_STATUS_IDLE
        await self._run_state_machine(new_status)

        # Track nozzle/laser hours
        await self._update_runtime_trackers(new_status)

        # Update maintenance sensor values
        await self._update_maintenance_values()

        result = {
            "print_status": new_status,
            "entities": self._entities,
            "counters": dict(self._store.counters),
            "maintenance": dict(self._store.get_maintenance()),
            "history": self._store.get_history(),
            "monthly": self._store.get_monthly_stats(),
            "last_print": self._store.get_last_print(),
        }
        return result

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    async def _run_state_machine(self, new_status: str) -> None:
        prev = self._print_status

        if prev == PRINT_STATUS_IDLE and new_status == PRINT_STATUS_PRINTING:
            await self._on_print_start()

        elif prev in (PRINT_STATUS_PRINTING, "pause") and new_status == PRINT_STATUS_FINISH:
            await self._on_print_finish()

        elif prev in (PRINT_STATUS_PRINTING, "pause") and new_status == PRINT_STATUS_FAILED:
            await self._on_print_failed()

        elif new_status == PRINT_STATUS_PRINTING and prev != PRINT_STATUS_PRINTING:
            # Resumed from pause or other state
            if self._print_start_time is None:
                await self._on_print_start()

        if new_status in TERMINAL_PRINT_STATUSES or new_status == PRINT_STATUS_IDLE:
            if prev in ACTIVE_PRINT_STATUSES | {PRINT_STATUS_PRINTING}:
                self._notify.reset_progress_tracker()
                self._print_start_time = None
                self._energy_at_start = None

        # Progress notifications while printing
        if new_status == PRINT_STATUS_PRINTING:
            progress_raw = get_entity_float(self.hass, self._entities, "print_progress")
            progress = int(progress_raw or 0)
            if self._notify.should_notify_progress(progress):
                remaining_raw = get_entity_float(self.hass, self._entities, "remaining_time") or 0
                remaining = _format_minutes(int(remaining_raw))
                printer_name = self._options.get(CONF_PRINTER_DISPLAY_NAME, "Bambu Lab")
                print_name = self._last_print_name
                await self._notify.notify_progress(
                    {
                        "drucker": printer_name,
                        "name": print_name,
                        "progress": progress,
                        "remaining": remaining,
                    }
                )

        self._print_status = new_status

    async def _on_print_start(self) -> None:
        self._print_start_time = datetime.now()
        self._last_print_name = get_entity_state(self.hass, self._entities, "subtask_name") or ""
        energy_entity_id = self._options.get(CONF_ENERGY_SENSOR)
        if energy_entity_id:
            raw_e = self.hass.states.get(energy_entity_id)
            if raw_e and raw_e.state not in ("unknown", "unavailable"):
                try:
                    self._energy_at_start = float(raw_e.state)
                except (ValueError, TypeError):
                    self._energy_at_start = None

    async def _on_print_finish(self) -> None:
        record = self._build_print_record(success=True)
        self._store.add_print(record)
        self._store.increment_counter("total_prints", 1)
        self._store.increment_counter("successful_prints", 1)
        self._store.increment_counter("total_print_time_min", record.get("duration_min", 0))
        self._store.increment_counter("total_energy_kwh", record.get("energy_kwh", 0))
        self._store.increment_counter("total_filament_g", record.get("filament_weight_g", 0))
        self._store.increment_counter("total_cost", record.get("total_cost", 0))
        await self._store.async_save()

        printer_name = self._options.get(CONF_PRINTER_DISPLAY_NAME, "Bambu Lab")
        currency = self._options.get(CONF_CURRENCY, DEFAULT_CURRENCY)
        await self._notify.notify_done(
            {
                "drucker": printer_name,
                "name": record.get("name", ""),
                "duration": _format_minutes(record.get("duration_min", 0)),
                "weight": f"{record.get('filament_weight_g', 0):.1f} g",
                "energy": f"{record.get('energy_kwh', 0):.3f} kWh",
                "cost": f"{currency}{record.get('total_cost', 0):.2f}",
            }
        )

    async def _on_print_failed(self) -> None:
        record = self._build_print_record(success=False)
        self._store.add_print(record)
        self._store.increment_counter("total_prints", 1)
        self._store.increment_counter("failed_prints", 1)
        await self._store.async_save()

        printer_name = self._options.get(CONF_PRINTER_DISPLAY_NAME, "Bambu Lab")
        progress_raw = get_entity_float(self.hass, self._entities, "print_progress")
        await self._notify.notify_error(
            {
                "drucker": printer_name,
                "name": record.get("name", ""),
                "progress": int(progress_raw or 0),
                "duration": _format_minutes(record.get("duration_min", 0)),
            }
        )

    def _build_print_record(self, success: bool) -> dict:
        now = datetime.now()
        start = self._print_start_time or now
        duration_min = int((now - start).total_seconds() / 60)

        progress_raw = get_entity_float(self.hass, self._entities, "print_progress") or 0
        filament_weight = get_entity_float(self.hass, self._entities, "print_weight") or 0
        bed_temp = get_entity_float(self.hass, self._entities, "bed_temp") or 0
        nozzle_temp = get_entity_float(self.hass, self._entities, "nozzle_temp") or 0
        layer_count = get_entity_float(self.hass, self._entities, "total_layers") or 0
        current_layer = get_entity_float(self.hass, self._entities, "current_layer") or 0
        nozzle_diameter = get_entity_float(self.hass, self._entities, "nozzle_diameter")
        nozzle_type = get_entity_state(self.hass, self._entities, "nozzle_type") or ""
        bed_type = get_entity_state(self.hass, self._entities, "print_bed_type") or ""
        name = get_entity_state(self.hass, self._entities, "subtask_name") or self._last_print_name
        gcode_file = get_entity_state(self.hass, self._entities, "gcode_file") or ""
        # Active tray / filament slot snapshot
        active_tray_name = get_entity_state(self.hass, self._entities, "active_tray") or ""
        active_tray_color = get_entity_attribute(self.hass, self._entities, "active_tray", "color") or ""
        active_tray_type = get_entity_attribute(self.hass, self._entities, "active_tray", "type") or ""
        active_tray_slot = get_entity_attribute(self.hass, self._entities, "active_tray", "tray_index")
        active_tray_ams = get_entity_attribute(self.hass, self._entities, "active_tray", "ams_index")
        cover_image_entity = self._entities.get("cover_image", "")

        # Energy calculation
        energy_kwh = 0.0
        energy_entity_id = self._options.get(CONF_ENERGY_SENSOR)
        if energy_entity_id and self._energy_at_start is not None:
            raw_e = self.hass.states.get(energy_entity_id)
            if raw_e and raw_e.state not in ("unknown", "unavailable"):
                try:
                    energy_kwh = max(0.0, float(raw_e.state) - self._energy_at_start)
                except (ValueError, TypeError):
                    energy_kwh = 0.0
        else:
            # Estimate from duration and a flat 100W assumption
            energy_kwh = duration_min / 60 * 0.1

        # Cost calculation
        electricity_price = float(self._options.get(CONF_ELECTRICITY_PRICE, DEFAULT_ELECTRICITY_PRICE))
        dynamic_sensor = self._options.get(CONF_ELECTRICITY_SENSOR)
        if dynamic_sensor:
            raw_p = self.hass.states.get(dynamic_sensor)
            if raw_p and raw_p.state not in ("unknown", "unavailable"):
                try:
                    electricity_price = float(raw_p.state)
                except (ValueError, TypeError):
                    pass

        filament_cost_per_kg = float(self._options.get(CONF_FILAMENT_COST, DEFAULT_FILAMENT_COST_PER_KG))
        filament_unit = self._options.get(CONF_FILAMENT_UNIT, "kg")
        if filament_unit == "g":
            filament_cost_per_g = filament_cost_per_kg / 1000
        else:
            filament_cost_per_g = filament_cost_per_kg / 1000

        energy_cost = energy_kwh * electricity_price
        filament_cost = filament_weight * filament_cost_per_g
        total_cost = energy_cost + filament_cost

        return {
            "timestamp_start": start.isoformat(),
            "timestamp_end": now.isoformat(),
            "name": name,
            "gcode_file": gcode_file,
            "status": "success" if success else "failed",
            "duration_min": duration_min,
            "progress_at_end": int(progress_raw),
            "filament_weight_g": filament_weight,
            "energy_kwh": energy_kwh,
            "filament_cost": filament_cost,
            "energy_cost": energy_cost,
            "total_cost": total_cost,
            "nozzle_diameter": nozzle_diameter,
            "nozzle_type": nozzle_type,
            "bed_type": bed_type,
            "avg_bed_temp": bed_temp,
            "avg_nozzle_temp": nozzle_temp,
            "layer_count": int(layer_count),
            "current_layer": int(current_layer),
            "active_tray": {
                "name": active_tray_name,
                "color": active_tray_color,
                "type": active_tray_type,
                "slot": active_tray_slot,
                "ams": active_tray_ams,
            },
            "cover_image_entity": cover_image_entity,
        }

    # ------------------------------------------------------------------
    # Runtime trackers (nozzle/laser hours)
    # ------------------------------------------------------------------

    async def _update_runtime_trackers(self, print_status: str) -> None:
        interval_h = UPDATE_INTERVAL.total_seconds() / 3600

        # Print hours
        if print_status == PRINT_STATUS_PRINTING:
            self._store.increment_counter("print_hours", interval_h)

        # Nozzle hours (single nozzle)
        if not self._features.get("dual_nozzle"):
            nozzle_temp = get_entity_float(self.hass, self._entities, "nozzle_temperature") or 0
            if nozzle_temp > NOZZLE_ACTIVE_TEMP_THRESHOLD and print_status == PRINT_STATUS_PRINTING:
                self._store.increment_counter("nozzle_hours", interval_h)

        # Nozzle hours (dual nozzle, H2D)
        if self._features.get("dual_nozzle"):
            left_temp = get_entity_float(self.hass, self._entities, "left_nozzle_temperature") or 0
            right_temp = get_entity_float(self.hass, self._entities, "right_nozzle_temperature") or 0
            if left_temp > NOZZLE_ACTIVE_TEMP_THRESHOLD and print_status == PRINT_STATUS_PRINTING:
                self._store.increment_counter("left_nozzle_hours", interval_h)
            if right_temp > NOZZLE_ACTIVE_TEMP_THRESHOLD and print_status == PRINT_STATUS_PRINTING:
                self._store.increment_counter("right_nozzle_hours", interval_h)

        # Laser hours (H2D)
        if self._features.get("laser"):
            tool_state = get_entity_state(self.hass, self._entities, "tool_module_state")
            if tool_state == "laser":
                self._store.increment_counter("laser_hours", interval_h)

        await self._store.async_save()

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def _update_maintenance_values(self) -> None:
        """Sync maintenance counters from global counters and fire notifications."""
        counters = self._store.counters
        has_ams = bool(self._ams_device_ids)
        tasks = get_applicable_tasks(self._model, has_ams)
        maint_intervals = self._options.get("maintenance_intervals", {})

        for task in tasks:
            key = task["key"]
            trigger = task["trigger"]
            default_interval = task["default_interval"]
            interval = float(maint_intervals.get(key, default_interval))

            current_value = self._get_trigger_value(trigger, counters)
            # Current value since last reset
            last_reset_value = float(self._store.get_maintenance().get(key, {}).get("baseline", 0))
            since_reset = max(0.0, current_value - last_reset_value)

            self._store.set_maintenance_value(key, since_reset)

            # Notification
            if is_maintenance_due(since_reset, interval):
                last_notified = self._maint_notified.get(key)
                if last_notified is None or (datetime.now() - last_notified).total_seconds() > 3600:
                    printer_name = self._options.get(CONF_PRINTER_DISPLAY_NAME, "Bambu Lab")
                    await self._notify.notify_maintenance(
                        {
                            "drucker": printer_name,
                            "wartung": task["name"],
                            "stunden": f"{since_reset:.1f}",
                            "intervall": f"{interval:.0f}",
                        }
                    )
                    self._maint_notified[key] = datetime.now()

    def _get_trigger_value(self, trigger: str, counters: dict) -> float:
        mapping = {
            "print_hours": "print_hours",
            "nozzle_hours": "nozzle_hours",
            "laser_hours": "laser_hours",
            "laser_jobs": "laser_jobs",
            "print_count": "successful_prints",
            "total_hours": "print_hours",  # fallback; ideally from total_usage_hours sensor
        }
        counter_key = mapping.get(trigger, trigger)
        return float(counters.get(counter_key, 0))

    # ------------------------------------------------------------------
    # Public reset helpers (called by buttons)
    # ------------------------------------------------------------------

    async def async_reset_nozzle(self) -> None:
        await self._reset_with_baseline("nozzle_clean", "nozzle_hours")

    async def async_reset_left_nozzle(self) -> None:
        await self._reset_with_baseline("left_nozzle_clean", "left_nozzle_hours")

    async def async_reset_right_nozzle(self) -> None:
        await self._reset_with_baseline("right_nozzle_clean", "right_nozzle_hours")

    async def async_reset_laser(self) -> None:
        await self._reset_with_baseline("laser_lens", "laser_hours")

    async def async_reset_maintenance_task(self, task_key: str) -> None:
        trigger_map = {t["key"]: t["trigger"] for t in MAINTENANCE_TASKS}
        trigger = trigger_map.get(task_key, "print_hours")
        counter_map = {
            "print_hours": "print_hours",
            "nozzle_hours": "nozzle_hours",
            "laser_hours": "laser_hours",
            "laser_jobs": "laser_jobs",
            "print_count": "successful_prints",
            "total_hours": "print_hours",
        }
        counter_key = counter_map.get(trigger, "print_hours")
        await self._reset_with_baseline(task_key, counter_key)

    async def _reset_with_baseline(self, task_key: str, counter_key: str) -> None:
        current = float(self._store.counters.get(counter_key, 0))
        maint = self._store.get_maintenance()
        if task_key not in maint:
            maint[task_key] = {}
        maint[task_key]["baseline"] = current
        maint[task_key]["value"] = 0
        maint[task_key]["last_reset"] = datetime.now().isoformat()
        self._maint_notified.pop(task_key, None)
        await self._store.async_save()
        await self.async_refresh()


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def _format_minutes(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"
