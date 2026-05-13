"""DataUpdateCoordinator for Bambu Print Tracker."""
from __future__ import annotations

import base64
import logging
import re
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    ACTIVE_PRINT_STATUSES,
    CONF_AMS_DEVICE_IDS,
    CONF_CURRENCY,
    CONF_DEVICE_ID,
    CONF_ELECTRICITY_PRICE,
    CONF_ELECTRICITY_SENSOR,
    CONF_ENERGY_SENSOR,
    CONF_FILAMENT_COST,
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
    PRINT_STATUS_PAUSE,
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
        self._notify = NotifyManager(hass, self._serial, self._options)

        # State machine
        self._print_status: str = PRINT_STATUS_IDLE
        self._print_start_time: datetime | None = None
        self._energy_at_start: float | None = None
        self._last_progress: int = 0
        self._last_print_name: str = ""
        self._last_cover_image_url: str = ""

        # Accumulated per-session seconds for nozzle/laser tracking
        self._nozzle_session_start: datetime | None = None
        self._left_nozzle_session_start: datetime | None = None
        self._right_nozzle_session_start: datetime | None = None
        self._laser_session_start: datetime | None = None

        # Cached entity maps (populated on first refresh)
        self._entities: dict[str, str] = {}

        # Maintenance notification cooldown: task_key → last notified datetime
        self._maint_notified: dict[str, datetime] = {}

        # Nozzle change detection
        self._last_nozzle_diameter: float | None = None
        self._last_nozzle_type: str | None = None
        self._nozzle_change_initialized: bool = False
        # Per-position tracking for dual-nozzle printers {position: {"diameter": x, "type": y}}
        self._last_nozzle_state: dict[str, dict] = {}

        # Graceful-degradation flags
        self._entities_missing_logged: bool = False  # throttle "no entities" warning
        self._printer_offline: bool = False  # True while status entity is unavailable

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def options(self) -> dict:
        """Merged view of entry data + options (options take precedence)."""
        return self._options

    @property
    def _printer_name(self) -> str:
        """Display name of the printer as configured by the user."""
        return self._options.get(CONF_PRINTER_DISPLAY_NAME, "Bambu Lab")

    # ------------------------------------------------------------------
    # Setup / Teardown
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Load stored data and set up state listeners."""
        await self._store.async_load()
        self._refresh_entity_maps()
        self._setup_state_listeners()
        self._setup_mobile_action_listener()

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
        self.hass.async_create_task(self.async_request_refresh())

    def _setup_mobile_action_listener(self) -> None:
        """Listen for mobile_app_notification_action events to handle nozzle-slot selection."""
        @callback
        def _on_mobile_action(event) -> None:
            action: str = event.data.get("action", "")
            prefix = f"bc_nozzle_slot_{self._serial}_"
            if not action.startswith(prefix):
                return
            rest = action[len(prefix):]          # e.g. "single_Düse 2"
            parts = rest.split("_", 1)
            if len(parts) != 2:
                return
            position, label = parts
            self.hass.async_create_task(
                self.async_select_nozzle_slot(position, label)
            )

        self._entry.async_on_unload(
            self.hass.bus.async_listen("mobile_app_notification_action", _on_mobile_action)
        )

    # ------------------------------------------------------------------
    # Core update
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        """Refresh all tracked values and run state machine."""
        try:
            return await self._async_update_data_inner()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error updating Bambu Companion data for %s", self._serial)
            # Return store-based fallback so the config entry stays loaded
            # and sensors remain available with their last known values.
            if self.data:
                return dict(self.data)
            return {
                "print_status": PRINT_STATUS_IDLE,
                "print_progress": 0,
                "entities": self._entities,
                "counters": dict(self._store.counters),
                "bambu_total_hours": None,
                "maintenance": dict(self._store.get_maintenance()),
                "history": self._store.get_history(),
                "monthly": self._store.get_monthly_stats(),
                "last_print": self._store.get_last_print(),
                "printer_offline": True,
                "nozzle_slots": {
                    "single": dict(self._store.get_nozzle_slots("single")),
                    "left": dict(self._store.get_nozzle_slots("left")),
                    "right": dict(self._store.get_nozzle_slots("right")),
                    "active": {
                        "single": self._store.get_active_nozzle_slot("single"),
                        "left": self._store.get_active_nozzle_slot("left"),
                        "right": self._store.get_active_nozzle_slot("right"),
                    },
                },
            }

    async def _async_update_data_inner(self) -> dict[str, Any]:
        """Inner update – exceptions here are caught by _async_update_data."""
        # Refresh entity maps in case entities changed
        self._refresh_entity_maps()

        # --- Graceful degradation: no entities yet (ha-bambulab not loaded) ---
        if not self._entities:
            if not self._entities_missing_logged:
                _LOGGER.warning(
                    "No ha-bambulab entities found for device %s (serial=%s). "
                    "Waiting for ha-bambulab to load.",
                    self._device_id,
                    self._serial,
                )
                self._entities_missing_logged = True
            # Return last cached coordinator data if available, otherwise build
            # from store so persistent counters are always visible in the UI.
            if self.data:
                return dict(self.data)
            return {
                "print_status": PRINT_STATUS_IDLE,
                "print_progress": 0,
                "entities": {},
                "counters": dict(self._store.counters),
                "bambu_total_hours": None,
                "maintenance": dict(self._store.get_maintenance()),
                "history": self._store.get_history(),
                "monthly": self._store.get_monthly_stats(),
                "last_print": self._store.get_last_print(),
                "printer_offline": True,
                "nozzle_slots": {
                    "single": dict(self._store.get_nozzle_slots("single")),
                    "left": dict(self._store.get_nozzle_slots("left")),
                    "right": dict(self._store.get_nozzle_slots("right")),
                    "active": {
                        "single": self._store.get_active_nozzle_slot("single"),
                        "left": self._store.get_active_nozzle_slot("left"),
                        "right": self._store.get_active_nozzle_slot("right"),
                    },
                },
            }
        else:
            self._entities_missing_logged = False  # reset once entities are available

        # --- Graceful degradation: printer offline ---
        status_entity_id = self._entities.get("print_status")
        raw_status_state = (
            self.hass.states.get(status_entity_id) if status_entity_id else None
        )
        _LOGGER.debug(
            "[%s] Poll: entity_map=%d keys, print_status_eid=%s, raw_state=%s, tracked=%s, start_time=%s",
            self._serial, len(self._entities), status_entity_id,
            raw_status_state.state if raw_status_state else None,
            self._print_status, self._print_start_time,
        )
        printer_is_offline = raw_status_state is None or raw_status_state.state in (
            "unavailable",
            "unknown",
        )

        if printer_is_offline:
            if not self._printer_offline:
                _LOGGER.info(
                    "Printer %s is offline or unavailable — holding current state.",
                    self._serial,
                )
                self._printer_offline = True
            # Hold current state: don't advance the state machine.
            # If we have cached coordinator data, use it; otherwise build from store
            # so persistent counters are visible even on first load while offline.
            if self.data:
                result = dict(self.data)
            else:
                result = {
                    "print_status": PRINT_STATUS_IDLE,
                    "print_progress": 0,
                    "entities": self._entities,
                    "counters": dict(self._store.counters),
                    "bambu_total_hours": None,
                    "maintenance": dict(self._store.get_maintenance()),
                    "history": self._store.get_history(),
                    "monthly": self._store.get_monthly_stats(),
                    "last_print": self._store.get_last_print(),
                    "nozzle_slots": {
                        "single": dict(self._store.get_nozzle_slots("single")),
                        "left": dict(self._store.get_nozzle_slots("left")),
                        "right": dict(self._store.get_nozzle_slots("right")),
                        "active": {
                            "single": self._store.get_active_nozzle_slot("single"),
                            "left": self._store.get_active_nozzle_slot("left"),
                            "right": self._store.get_active_nozzle_slot("right"),
                        },
                    },
                }
            result["printer_offline"] = True
            return result
        else:
            if self._printer_offline:
                _LOGGER.info("Printer %s is back online.", self._serial)
                self._printer_offline = False

        new_status = raw_status_state.state if raw_status_state else PRINT_STATUS_IDLE
        await self._run_state_machine(new_status)

        # While printing: continuously refresh name and cover image so we always
        # have the latest values even if they were unavailable at print start.
        if new_status in (PRINT_STATUS_PRINTING, PRINT_STATUS_PAUSE):
            live_name = get_entity_state(self.hass, self._entities, "subtask_name") or ""
            if live_name:
                self._last_print_name = live_name
            cover_img_eid = self._entities.get("cover_image", "")
            if cover_img_eid:
                cov_state = self.hass.states.get(cover_img_eid)
                if cov_state:
                    url = cov_state.attributes.get("entity_picture", "")
                    if url:
                        self._last_cover_image_url = url

        # Track nozzle/laser hours
        await self._update_runtime_trackers(new_status)

        # Update maintenance sensor values
        await self._update_maintenance_values()

        # Detect nozzle type/size change and notify user
        await self._detect_nozzle_change()

        # Read total_usage_hours from ha-bambulab and prefer it over the internal counter.
        # If the entity is unavailable or temporarily 0 (e.g. during printer shutdown /
        # reconnect), keep the last known non-zero value to prevent the sensor from
        # resetting to 0.
        _new_bambu_hours = get_entity_float(self.hass, self._entities, "total_usage_hours")
        _last_bambu_hours = (self.data or {}).get("bambu_total_hours")
        if _new_bambu_hours:
            bambu_total_hours = _new_bambu_hours
        else:
            bambu_total_hours = _last_bambu_hours  # preserve last known value (may be None)

        print_progress = int(get_entity_float(self.hass, self._entities, "print_progress") or 0)

        result = {
            "print_status": new_status,
            "print_progress": print_progress,
            "entities": self._entities,
            "counters": dict(self._store.counters),
            "bambu_total_hours": bambu_total_hours,
            "maintenance": dict(self._store.get_maintenance()),
            "history": self._store.get_history(),
            "monthly": self._store.get_monthly_stats(),
            "last_print": self._store.get_last_print(),
            "printer_offline": False,
            "nozzle_slots": {
                "single": dict(self._store.get_nozzle_slots("single")),
                "left": dict(self._store.get_nozzle_slots("left")),
                "right": dict(self._store.get_nozzle_slots("right")),
                "active": {
                    "single": self._store.get_active_nozzle_slot("single"),
                    "left": self._store.get_active_nozzle_slot("left"),
                    "right": self._store.get_active_nozzle_slot("right"),
                },
            },
        }
        return result

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    async def _run_state_machine(self, new_status: str) -> None:
        prev = self._print_status
        _LOGGER.info(
            "[%s] State machine: '%s' → '%s'  (start_time=%s, entity_map_keys=%s)",
            self._serial, prev, new_status, self._print_start_time,
            list(self._entities.keys()),
        )

        if prev == PRINT_STATUS_IDLE and new_status == PRINT_STATUS_PRINTING:
            await self._on_print_start()

        elif new_status == PRINT_STATUS_FINISH:
            # Handle finish regardless of prev state.
            # prev=printing/pause: normal case.
            # prev=finish: printer stays in finish across multiple polls — silently ignore.
            # prev=idle with no tracked start: integration started while printer was already
            #   in finish (or print completed between HA restarts) — nothing to record.
            # prev=idle with tracked start: HA was reloaded mid-print, missed the printing state.
            if prev == PRINT_STATUS_FINISH:
                pass  # Idempotent — printer staying in finish, nothing to do.
            elif prev in (PRINT_STATUS_PRINTING, PRINT_STATUS_PAUSE):
                await self._on_print_finish()
            elif self._print_start_time is not None:
                _LOGGER.info(
                    "[%s] finish state seen with prev='%s' but start was tracked — recording.",
                    self._serial, prev,
                )
                await self._on_print_finish()
            else:
                # Expected at startup if printer was already in finish when integration loaded.
                _LOGGER.debug(
                    "[%s] finish state seen but no print was tracked (prev='%s') — skipping. "
                    "This is normal at startup if the printer was already in finish state.",
                    self._serial, prev,
                )

        elif prev in (PRINT_STATUS_PRINTING, PRINT_STATUS_PAUSE) and new_status == PRINT_STATUS_FAILED:
            await self._on_print_failed()

        elif prev in (PRINT_STATUS_PRINTING, PRINT_STATUS_PAUSE) and new_status == PRINT_STATUS_IDLE:
            # Printer went directly printing/pause → idle, skipping the "finish" state.
            # This happens when the "finish" status is only visible for a few seconds
            # and falls between two 30-second polls (common on H2D and other models).
            # Treat this as a successful print completion.
            if self._print_start_time is not None:
                _LOGGER.info(
                    "[%s] status jumped '%s' → idle (finish state missed by poll interval). "
                    "Recording as successful print.",
                    self._serial, prev,
                )
                await self._on_print_finish()
            else:
                _LOGGER.warning(
                    "[%s] '%s' → idle but _print_start_time is None — skipping record. "
                    "This means _on_print_start() was never called for this print. "
                    "Check that the 'printing' state was seen before this transition.",
                    self._serial, prev,
                )

        elif new_status == PRINT_STATUS_PRINTING and prev != PRINT_STATUS_PRINTING:
            # Resumed from pause or other state
            _LOGGER.debug("[%s] '%s' → printing — treating as resumed/started.", self._serial, prev)
            if self._print_start_time is None:
                await self._on_print_start()

        else:
            _LOGGER.debug(
                "[%s] No action for '%s' → '%s' (start_time=%s).",
                self._serial, prev, new_status, self._print_start_time,
            )

        if new_status in TERMINAL_PRINT_STATUSES or new_status == PRINT_STATUS_IDLE:
            # Always clear the tracked start time when a terminal/idle state is reached,
            # regardless of what prev was (covers the idle→finish edge case above).
            if self._print_start_time is not None or prev in ACTIVE_PRINT_STATUSES:
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
                printer_name = self._printer_name
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
        self._print_start_time = dt_util.now()
        self._last_print_name = get_entity_state(self.hass, self._entities, "subtask_name") or ""
        _LOGGER.info(
            "[%s] Print started: name='%s', start_time=%s",
            self._serial, self._last_print_name, self._print_start_time,
        )
        printer_name = self._printer_name
        await self._notify.notify_start(
            {"drucker": printer_name, "name": self._last_print_name}
        )
        energy_entity_id = self._options.get(CONF_ENERGY_SENSOR)
        if energy_entity_id:
            raw_e = self.hass.states.get(energy_entity_id)
            if raw_e and raw_e.state not in ("unknown", "unavailable"):
                try:
                    self._energy_at_start = float(raw_e.state)
                except (ValueError, TypeError):
                    self._energy_at_start = None

    async def _on_print_finish(self) -> None:
        _LOGGER.info(
            "[%s] Print finished – recording result (start_time=%s)",
            self._serial, self._print_start_time,
        )
        record = self._build_print_record(success=True)
        self._store.add_print(record)
        self._store.increment_counter("total_prints", 1)
        self._store.increment_counter("successful_prints", 1)
        self._store.increment_counter("total_print_time_min", record.get("duration_min", 0))
        self._store.increment_counter("total_energy_kwh", record.get("energy_kwh", 0))
        self._store.increment_counter("total_filament_g", record.get("filament_weight_g", 0))
        self._store.increment_counter("total_cost", record.get("total_cost", 0))
        self._store.increment_counter("total_filament_cost", record.get("filament_cost", 0))
        self._store.increment_counter("total_energy_cost", record.get("energy_cost", 0))
        try:
            await self._store.async_save()
        except Exception:
            _LOGGER.exception("[%s] Failed to persist print record to storage", self._serial)

        printer_name = self._printer_name
        currency = self._options.get(CONF_CURRENCY, DEFAULT_CURRENCY)
        variables = {
            "drucker": printer_name,
            "name": record.get("name", ""),
            "duration": _format_minutes(record.get("duration_min", 0)),
            "weight": f"{record.get('filament_weight_g', 0):.1f} g",
            "energy": f"{record.get('energy_kwh', 0):.3f} kWh",
            "cost": f"{currency}{record.get('total_cost', 0):.2f}",
        }
        _LOGGER.info(
            "[%s] Print record saved – total_prints now %s, sending notifications",
            self._serial, self._store.counters.get("total_prints"),
        )
        await self._notify.notify_done(variables)

    async def _on_print_failed(self) -> None:
        _LOGGER.info(
            "[%s] Print failed – recording result (start_time=%s)",
            self._serial, self._print_start_time,
        )
        record = self._build_print_record(success=False)
        self._store.add_print(record)
        self._store.increment_counter("total_prints", 1)
        self._store.increment_counter("failed_prints", 1)
        await self._store.async_save()

        printer_name = self._printer_name
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
        now = dt_util.now()
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
        # Last resort: extract filename from gcode_file path if name is still empty
        if not name and gcode_file:
            import os
            name = os.path.splitext(os.path.basename(gcode_file))[0]
            # Also strip .gcode if double-extension like .gcode.3mf
            name = re.sub(r'\.gcode$', '', name, flags=re.IGNORECASE)
        plate, project_name = _extract_plate_info(gcode_file)
        # Active tray / filament slot snapshot
        active_tray_name = get_entity_state(self.hass, self._entities, "active_tray") or ""
        active_tray_color = get_entity_attribute(self.hass, self._entities, "active_tray", "color") or ""
        active_tray_type = get_entity_attribute(self.hass, self._entities, "active_tray", "type") or ""
        active_tray_slot = get_entity_attribute(self.hass, self._entities, "active_tray", "tray_index")
        active_tray_ams = get_entity_attribute(self.hass, self._entities, "active_tray", "ams_index")
        cover_image_entity = self._entities.get("cover_image", "")
        # Fetch the raw image bytes from the HA image entity and encode as base64
        # data-URL so the history card can display it without relying on a
        # token-based proxy URL (which expires after the next image update).
        cover_image_data = ""
        if cover_image_entity:
            try:
                from homeassistant.components.image import async_get_image
                img = await async_get_image(self.hass, cover_image_entity)
                if img and img.content:
                    b64 = base64.b64encode(img.content).decode("utf-8")
                    mime = img.content_type or "image/jpeg"
                    cover_image_data = f"data:{mime};base64,{b64}"
            except Exception:
                _LOGGER.debug("[%s] Could not fetch cover image bytes", self._serial)
        _LOGGER.info(
            "[%s] _build_print_record: name=%r, cover_image_entity=%r, has_image=%s",
            self._serial, name, cover_image_entity, bool(cover_image_data),
        )

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
        filament_cost_per_g = filament_cost_per_kg / 1000

        energy_cost = energy_kwh * electricity_price
        filament_cost = filament_weight * filament_cost_per_g
        total_cost = energy_cost + filament_cost

        return {
            "timestamp_start": start.isoformat(),
            "timestamp_end": now.isoformat(),
            "name": name,
            "gcode_file": gcode_file,
            "project_name": project_name,
            "plate": plate,
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
            "cover_image_url": cover_image_data,
        }
        # Reset cached cover image after recording so next print starts fresh.
        self._last_cover_image_url = ""

    # ------------------------------------------------------------------
    # Runtime trackers (nozzle/laser hours)
    # ------------------------------------------------------------------

    async def _update_runtime_trackers(self, print_status: str) -> None:
        interval_h = UPDATE_INTERVAL.total_seconds() / 3600
        changed = False

        # Print hours
        if print_status == PRINT_STATUS_PRINTING:
            self._store.increment_counter("print_hours", interval_h)
            changed = True

        # Nozzle hours (single nozzle)
        if not self._features.get("dual_nozzle"):
            nozzle_temp = get_entity_float(self.hass, self._entities, "nozzle_temperature") or 0
            if nozzle_temp > NOZZLE_ACTIVE_TEMP_THRESHOLD and print_status == PRINT_STATUS_PRINTING:
                self._store.increment_nozzle_slot_hours("single", interval_h)
                # Keep legacy counter in sync so existing maintenance baselines still work
                self._store.increment_counter("nozzle_hours", interval_h)
                changed = True

        # Nozzle hours (dual nozzle, H2D)
        if self._features.get("dual_nozzle"):
            left_temp = get_entity_float(self.hass, self._entities, "left_nozzle_temperature") or 0
            right_temp = get_entity_float(self.hass, self._entities, "right_nozzle_temperature") or 0
            if left_temp > NOZZLE_ACTIVE_TEMP_THRESHOLD and print_status == PRINT_STATUS_PRINTING:
                self._store.increment_nozzle_slot_hours("left", interval_h)
                self._store.increment_counter("left_nozzle_hours", interval_h)
                changed = True
            if right_temp > NOZZLE_ACTIVE_TEMP_THRESHOLD and print_status == PRINT_STATUS_PRINTING:
                self._store.increment_nozzle_slot_hours("right", interval_h)
                self._store.increment_counter("right_nozzle_hours", interval_h)
                changed = True

        # Laser hours and jobs (H2D)
        if self._features.get("laser"):
            tool_state = get_entity_state(self.hass, self._entities, "tool_module_state")
            was_lasering = getattr(self, "_was_lasering", False)
            is_lasering = tool_state == "laser"
            if is_lasering:
                self._store.increment_counter("laser_hours", interval_h)
                changed = True
            if was_lasering and not is_lasering:
                # Transition: laser job completed
                self._store.increment_counter("laser_jobs", 1)
                changed = True
            self._was_lasering = is_lasering

        if changed:
            await self._store.async_save()

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def _update_maintenance_values(self) -> None:
        """Sync maintenance counters from global counters and fire notifications."""
        counters = self._store.counters
        bambu_total_hours = self.data.get("bambu_total_hours") if self.data else None
        has_ams = bool(self._ams_device_ids)
        tasks = get_applicable_tasks(self._model, has_ams)
        maint_intervals = self._options.get("maintenance_intervals", {})

        for task in tasks:
            key = task["key"]
            trigger = task["trigger"]
            default_interval = task["default_interval"]
            interval = float(maint_intervals.get(key, default_interval))

            # Whether this trigger uses the absolute bambu_total_hours sensor
            uses_bambu = (trigger == "total_hours" and bambu_total_hours is not None)
            current_value = self._get_trigger_value(trigger, counters, bambu_total_hours)

            maint_entry = self._store.get_maintenance().get(key)
            if maint_entry is None or "baseline" not in maint_entry:
                # First time seeing this task, OR migrating from old storage
                # that predates the baseline-tracking feature.  In both cases
                # we re-baseline to the current value so no false alert fires.
                if maint_entry is not None:
                    _LOGGER.info(
                        "Migrating maintenance task '%s' for %s: "
                        "old storage has no baseline field – re-baselining to %.1f",
                        key, self._serial, current_value,
                    )
                self._store.set_maintenance_baseline(key, current_value, from_bambu=uses_bambu)
                await self._store.async_save()
                since_reset = 0.0
            else:
                # Re-baseline if the previous baseline was set using the internal
                # fallback counter (bambu_total_hours was None at that time) but
                # real bambu hours are now available.  Without this, the delta
                # between 0 h (fallback baseline) and e.g. 1000 h (real bambu
                # hours) would trigger false maintenance notifications.
                baseline_from_fallback = maint_entry.get("baseline_from_fallback", False)
                if baseline_from_fallback and uses_bambu:
                    _LOGGER.info(
                        "Re-baselining maintenance task '%s' for %s: "
                        "replacing fallback baseline %.1f with real bambu_total_hours %.1f",
                        key, self._serial,
                        float(maint_entry.get("baseline", 0)), current_value,
                    )
                    self._store.set_maintenance_baseline(key, current_value, from_bambu=True)
                    await self._store.async_save()
                    since_reset = 0.0
                else:
                    # Current value since last reset
                    last_reset_value = float(maint_entry.get("baseline", 0))
                    since_reset = max(0.0, current_value - last_reset_value)

            self._store.set_maintenance_value(key, since_reset)

            # Notification – max once per 24 hours, persisted across HA restarts
            if is_maintenance_due(since_reset, interval):
                now = dt_util.now()
                # Check in-memory cache first (fast path), then fall back to storage
                last_notified = self._maint_notified.get(key) or self._store.get_maintenance_last_notified(key)
                cooldown_seconds = 24 * 3600  # 24 h
                if last_notified is None or (now - last_notified).total_seconds() > cooldown_seconds:
                    printer_name = self._printer_name
                    await self._notify.notify_maintenance(
                        {
                            "drucker": printer_name,
                            "wartung": task["name"],
                            "stunden": f"{since_reset:.1f}",
                            "intervall": f"{interval:.0f}",
                        }
                    )
                    self._maint_notified[key] = now
                    self._store.set_maintenance_last_notified(key, now)
                    await self._store.async_save()

    # ------------------------------------------------------------------
    # Nozzle change detection
    # ------------------------------------------------------------------

    async def _detect_nozzle_change(self) -> None:
        """Detect nozzle diameter/type changes per position and notify the user."""
        # Map position → (diameter_key, type_key) using ha-bambulab translation_keys.
        # Source: github.com/greghesp/ha-bambulab definitions.py
        # Keys are "nozzle_diameter" / "left_nozzle_diameter" / "right_nozzle_diameter".
        if self._features.get("dual_nozzle"):
            positions = {
                "left": ("left_nozzle_diameter", "left_nozzle_type"),
                "right": ("right_nozzle_diameter", "right_nozzle_type"),
            }
        else:
            positions = {
                "single": ("nozzle_diameter", "nozzle_type"),
            }

        for position, (diameter_key, type_key) in positions.items():
            diameter = get_entity_float(self.hass, self._entities, diameter_key)
            nozzle_type = get_entity_state(self.hass, self._entities, type_key) or ""

            if diameter is None:
                continue  # entity not yet available

            prev = self._last_nozzle_state.get(position)
            if prev is None:
                # First run – memorise without notifying
                self._last_nozzle_state[position] = {"diameter": diameter, "type": nozzle_type}
                continue

            diameter_changed = prev["diameter"] != diameter
            type_changed = nozzle_type != "" and prev["type"] != nozzle_type

            if diameter_changed or type_changed:
                _LOGGER.info(
                    "Nozzle change detected on %s (%s): %.2fmm %s → %.2fmm %s",
                    self._serial, position,
                    prev["diameter"] or 0, prev["type"],
                    diameter, nozzle_type,
                )
                self._last_nozzle_state[position] = {"diameter": diameter, "type": nozzle_type}

                labels = self.get_nozzle_slot_labels(position)
                active = self.get_active_nozzle_label(position)
                await self._notify.notify_nozzle_change(
                    {
                        "drucker": self._printer_name,
                        "serial": self._serial,
                        "position": position,
                        "diameter": diameter,
                        "nozzle_type": nozzle_type,
                        "labels": labels,
                        "active": active,
                    }
                )

    def _get_trigger_value(self, trigger: str, counters: dict, bambu_total_hours: float | None = None) -> float:
        if trigger == "total_hours" and bambu_total_hours is not None:
            return bambu_total_hours
        mapping = {
            "print_hours": "print_hours",
            "nozzle_hours": "nozzle_hours",
            "laser_hours": "laser_hours",
            "laser_jobs": "laser_jobs",
            "print_count": "successful_prints",
            "total_hours": "print_hours",  # fallback when bambu sensor unavailable
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

        # If the task has reset_counter=True (e.g. nozzle replacement),
        # zero the underlying counter so hours count from scratch.
        task_def = next((t for t in MAINTENANCE_TASKS if t["key"] == task_key), {})
        if task_def.get("reset_counter", False):
            # Use explicit counter_key override when provided (e.g. left/right nozzle)
            actual_counter = task_def.get("counter_key", counter_key)
            self._store.set_counter(actual_counter, 0)

        # For total_hours tasks, reset against real bambu_total_hours if available
        if trigger == "total_hours":
            bambu_total_hours = (self.data or {}).get("bambu_total_hours")
            if bambu_total_hours is not None:
                self._store.set_maintenance_baseline(task_key, bambu_total_hours, from_bambu=True)
                maint = self._store.get_maintenance()
                maint[task_key]["value"] = 0
                maint[task_key]["last_reset"] = dt_util.now().isoformat()
                self._maint_notified.pop(task_key, None)
                await self._store.async_save()
                await self.async_request_refresh()
                return

        await self._reset_with_baseline(task_key, counter_key)

    async def _reset_with_baseline(self, task_key: str, counter_key: str) -> None:
        current = float(self._store.counters.get(counter_key, 0))
        maint = self._store.get_maintenance()
        if task_key not in maint:
            maint[task_key] = {}
        maint[task_key]["baseline"] = current
        maint[task_key]["value"] = 0
        maint[task_key]["last_reset"] = dt_util.now().isoformat()
        self._maint_notified.pop(task_key, None)
        await self._store.async_save()
        await self.async_refresh()

    # ------------------------------------------------------------------
    # Nozzle slot management (called by select / button entities)
    # ------------------------------------------------------------------

    def get_nozzle_slot_labels(self, position: str) -> list[str]:
        """Return ordered list of slot labels for the given position."""
        slots = self._store.get_nozzle_slots(position)
        return [slots[k]["label"] for k in sorted(slots.keys(), key=lambda x: int(x) if x.isdigit() else 0)]

    def get_active_nozzle_label(self, position: str) -> str | None:
        """Return the label of the currently active slot."""
        slots = self._store.get_nozzle_slots(position)
        active_id = self._store.get_active_nozzle_slot(position)
        return slots.get(active_id, {}).get("label")

    async def async_select_nozzle_slot(self, position: str, label: str) -> None:
        """Activate the slot with the given label."""
        slots = self._store.get_nozzle_slots(position)
        for slot_id, slot_data in slots.items():
            if slot_data["label"] == label:
                self._store.set_active_nozzle_slot(position, slot_id)
                await self._store.async_save()
                await self.async_refresh()
                return

    async def async_add_nozzle_slot(self, position: str) -> str:
        """Add a new nozzle slot, activate it, return its label."""
        new_id = self._store.add_nozzle_slot(position)
        new_label = self._store.get_nozzle_slots(position)[new_id]["label"]
        await self._store.async_save()
        await self.async_refresh()
        return new_label

    async def async_reset_active_nozzle_slot(self, position: str) -> None:
        """Reset hours of the currently active nozzle slot to 0."""
        self._store.reset_nozzle_slot_hours(position)
        await self._store.async_save()
        await self.async_refresh()

    async def async_rename_nozzle_slot(self, position: str, slot_id: str, new_label: str) -> None:
        """Rename a specific nozzle slot and refresh."""
        self._store.rename_nozzle_slot(position, slot_id, new_label)
        await self._store.async_save()
        await self.async_refresh()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_plate_info(gcode_file: str) -> tuple[str | None, str | None]:
    """Extract plate label and project name from a Bambu gcode_file path.

    Bambu paths look like:
      cache/MyModel/Metadata/plate_2.gcode.3mf
      cache/MyModel/plate_1.gcode
      /sdcard/gcodes/plate_3.gcode.3mf

    Returns (plate, project_name), both None when not determinable.
    """
    if not gcode_file:
        return None, None

    # Plate number
    plate: str | None = None
    m = re.search(r'plate[_\s]?(\d+)', gcode_file, re.IGNORECASE)
    if m:
        plate = f"Plate {m.group(1)}"

    # Project name: directory component just below cache/
    # e.g. cache/MyModel/Metadata/plate_2.gcode.3mf  →  "MyModel"
    project_name: str | None = None
    parts = re.split(r'[\\/]', gcode_file)
    try:
        cache_idx = next(i for i, p in enumerate(parts) if p.lower() in ("cache", "gcodes"))
        candidate = parts[cache_idx + 1] if cache_idx + 1 < len(parts) else None
        # Skip if the candidate looks like a filename itself
        if candidate and not re.search(r'\.(gcode|3mf|gcode\.3mf)$', candidate, re.IGNORECASE):
            project_name = candidate
    except StopIteration:
        pass

    return plate, project_name


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def _format_minutes(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"
