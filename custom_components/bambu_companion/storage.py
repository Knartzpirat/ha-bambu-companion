"""Storage backend for Bambu Print Tracker print history."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DEFAULT_MAX_HISTORY, DOMAIN, STORAGE_VERSION

STORAGE_KEY_TEMPLATE = f"{DOMAIN}_{{serial}}"


class PrintHistoryStore:
    """Manages persistent print history for one printer."""

    def __init__(self, hass: HomeAssistant, serial: str, max_history: int = DEFAULT_MAX_HISTORY) -> None:
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY_TEMPLATE.format(serial=serial))
        self._max_history = max_history
        self._data: dict[str, Any] = {}

    async def async_load(self) -> None:
        """Load data from storage."""
        stored = await self._store.async_load()
        if stored is None:
            self._data = {
                "history": [],
                "maintenance": {},
                "counters": {
                    "print_hours": 0.0,
                    "total_prints": 0,
                    "successful_prints": 0,
                    "failed_prints": 0,
                    "total_print_time_min": 0,
                    "total_energy_kwh": 0.0,
                    "total_filament_g": 0.0,
                    "total_cost": 0.0,
                    "nozzle_hours": 0.0,
                    "left_nozzle_hours": 0.0,
                    "right_nozzle_hours": 0.0,
                    "laser_hours": 0.0,
                    "laser_jobs": 0,
                },
            }
        else:
            self._data = stored

    async def async_save(self) -> None:
        """Persist data to storage."""
        await self._store.async_save(self._data)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def add_print(self, record: dict) -> None:
        """Add a completed print record, trimming to max_history."""
        if "id" not in record:
            record["id"] = str(uuid.uuid4())
        history: list = self._data.setdefault("history", [])
        history.insert(0, record)
        if self._max_history > 0 and len(history) > self._max_history:
            self._data["history"] = history[: self._max_history]

    def get_history(self) -> list[dict]:
        return self._data.get("history", [])

    def get_last_print(self) -> dict | None:
        history = self.get_history()
        return history[0] if history else None

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------

    @property
    def counters(self) -> dict:
        return self._data.setdefault("counters", {})

    def increment_counter(self, key: str, value: float | int) -> None:
        self.counters[key] = self.counters.get(key, 0) + value

    def set_counter(self, key: str, value: float | int) -> None:
        self.counters[key] = value

    def get_counter(self, key: str, default=0):
        return self.counters.get(key, default)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def get_maintenance(self) -> dict:
        return self._data.setdefault("maintenance", {})

    def reset_maintenance_task(self, task_key: str) -> None:
        """Reset a maintenance task counter to 0 (without baseline tracking).

        NOTE: The coordinator uses _reset_with_baseline() which also updates
        the baseline counter so hours are tracked relative to the reset point.
        This method is kept for direct storage-level resets only.
        """
        maint = self.get_maintenance()
        maint[task_key] = {
            "value": 0,
            "last_reset": dt_util.now().isoformat(),
        }

    def get_maintenance_value(self, task_key: str) -> float:
        maint = self.get_maintenance()
        entry = maint.get(task_key, {})
        return float(entry.get("value", 0))

    def set_maintenance_value(self, task_key: str, value: float) -> None:
        maint = self.get_maintenance()
        if task_key not in maint:
            maint[task_key] = {}
        maint[task_key]["value"] = value

    # ------------------------------------------------------------------
    # Nozzle slots (per-physical-nozzle hour tracking)
    # ------------------------------------------------------------------

    def get_nozzle_slots(self, position: str = "single") -> dict:
        """Return slot dict for a nozzle position (single / left / right)."""
        slots_root = self._data.setdefault("nozzle_slots", {})
        if position not in slots_root:
            label = {"single": "Düse 1", "left": "Linke Düse 1", "right": "Rechte Düse 1"}.get(position, f"Düse 1")
            slots_root[position] = {"1": {"hours": 0.0, "label": label}}
        return slots_root[position]

    def get_active_nozzle_slot(self, position: str = "single") -> str:
        """Return the currently active slot id for a position."""
        active_root = self._data.setdefault("active_nozzle", {})
        return active_root.get(position, "1")

    def set_active_nozzle_slot(self, position: str, slot_id: str) -> None:
        self._data.setdefault("active_nozzle", {})[position] = slot_id

    def add_nozzle_slot(self, position: str = "single") -> str:
        """Add a new slot, set it as active, return its slot_id."""
        slots = self.get_nozzle_slots(position)
        existing_nums = [int(k) for k in slots if k.isdigit()]
        new_id = str(max(existing_nums, default=0) + 1)
        prefix = {"single": "Düse", "left": "Linke Düse", "right": "Rechte Düse"}.get(position, "Düse")
        slots[new_id] = {"hours": 0.0, "label": f"{prefix} {new_id}"}
        self.set_active_nozzle_slot(position, new_id)
        return new_id

    def increment_nozzle_slot_hours(self, position: str, value: float) -> None:
        """Increment hours for the currently active slot."""
        slots = self.get_nozzle_slots(position)
        active = self.get_active_nozzle_slot(position)
        if active in slots:
            slots[active]["hours"] = slots[active].get("hours", 0.0) + value

    def get_active_nozzle_slot_hours(self, position: str = "single") -> float:
        slots = self.get_nozzle_slots(position)
        active = self.get_active_nozzle_slot(position)
        return float(slots.get(active, {}).get("hours", 0.0))

    def reset_nozzle_slot_hours(self, position: str) -> None:
        """Reset hours of the active slot to 0."""
        slots = self.get_nozzle_slots(position)
        active = self.get_active_nozzle_slot(position)
        if active in slots:
            slots[active]["hours"] = 0.0

    # ------------------------------------------------------------------
    # Monthly stats
    # ------------------------------------------------------------------

    def get_monthly_stats(self) -> dict:
        """Compute current-month stats from history."""
        now = dt_util.now()
        month_prints = 0
        month_cost = 0.0

        for record in self.get_history():
            ts = record.get("timestamp_start", "")
            try:
                dt = datetime.fromisoformat(ts)
                if dt.year == now.year and dt.month == now.month:
                    month_prints += 1
                    month_cost += float(record.get("total_cost", 0))
            except (ValueError, TypeError):
                continue

        return {"monthly_prints": month_prints, "monthly_cost": month_cost}
