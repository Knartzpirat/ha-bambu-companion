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

    def get_maintenance_last_notified(self, task_key: str) -> datetime | None:
        """Return the datetime of the last maintenance notification, or None."""
        maint = self.get_maintenance()
        raw = maint.get(task_key, {}).get("last_notified")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except (ValueError, TypeError):
            return None

    def set_maintenance_last_notified(self, task_key: str, when: datetime) -> None:
        """Persist the timestamp of the last maintenance notification."""
        maint = self.get_maintenance()
        if task_key not in maint:
            maint[task_key] = {}
        maint[task_key]["last_notified"] = when.isoformat()

    def set_maintenance_baseline(
        self, task_key: str, baseline: float, from_bambu: bool = False
    ) -> None:
        """Set the baseline for a task (used on first init and after reset).

        Args:
            from_bambu: True when the baseline value comes from the real
                bambu_total_hours sensor.  False means a fallback counter
                (internal print_hours) was used because bambu data was not
                yet available.
        """
        maint = self.get_maintenance()
        if task_key not in maint:
            maint[task_key] = {}
        maint[task_key]["baseline"] = baseline
        maint[task_key]["baseline_from_fallback"] = not from_bambu
        maint[task_key].setdefault("value", 0.0)

    # ------------------------------------------------------------------
    # Nozzle pool (shared across all physical positions)
    # ------------------------------------------------------------------

    def _migrate_to_pool(self) -> None:
        """One-time migration from per-position nozzle_slots to shared nozzle_pool."""
        if "nozzle_pool" in self._data:
            return
        old_slots = self._data.get("nozzle_slots", {})
        old_active = self._data.get("active_nozzle", {})
        pool: dict = {}
        new_active: dict = {}
        next_id = 1
        for pos in ("single", "left", "right"):
            pos_slots = old_slots.get(pos, {})
            pos_active_old = old_active.get(pos, "1")
            for slot_id in sorted(pos_slots.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                slot_data = pos_slots[slot_id]
                new_slot_id = str(next_id)
                pool[new_slot_id] = {
                    "hours": float(slot_data.get("hours", 0.0)),
                    "label": slot_data.get("label", f"Düse {next_id}"),
                }
                if slot_id == pos_active_old and pos not in new_active:
                    new_active[pos] = new_slot_id
                next_id += 1
        if not pool:
            pool["1"] = {"hours": 0.0, "label": "Düse 1"}
            new_active = {"single": "1", "left": "1", "right": "1"}
        else:
            # Ensure every position has an active entry
            default_id = sorted(pool.keys(), key=lambda x: int(x) if x.isdigit() else 0)[0]
            for pos in ("single", "left", "right"):
                new_active.setdefault(pos, default_id)
        self._data["nozzle_pool"] = pool
        self._data["active_nozzle"] = new_active

    def get_nozzle_pool(self) -> dict:
        """Return the shared nozzle pool dict (slot_id → {label, hours})."""
        self._migrate_to_pool()
        return self._data.setdefault("nozzle_pool", {"1": {"hours": 0.0, "label": "Düse 1"}})

    # Keep backward-compat alias (returns full pool regardless of position)
    def get_nozzle_slots(self, position: str = "single") -> dict:
        return self.get_nozzle_pool()

    def get_active_nozzle_slot(self, position: str = "single") -> str:
        """Return the currently active pool slot id for a position."""
        self._migrate_to_pool()
        active_root = self._data.setdefault("active_nozzle", {})
        pool = self.get_nozzle_pool()
        default = sorted(pool.keys(), key=lambda x: int(x) if x.isdigit() else 0)[0] if pool else "1"
        return active_root.get(position, default)

    def set_active_nozzle_slot(self, position: str, slot_id: str) -> None:
        self._migrate_to_pool()
        self._data.setdefault("active_nozzle", {})[position] = slot_id

    def add_nozzle_slot(self, position: str = "single") -> str:
        """Add a new slot to the shared pool, activate it for position, return slot_id."""
        pool = self.get_nozzle_pool()
        existing_nums = [int(k) for k in pool if k.isdigit()]
        new_id = str(max(existing_nums, default=0) + 1)
        pool[new_id] = {"hours": 0.0, "label": f"Düse {new_id}"}
        self.set_active_nozzle_slot(position, new_id)
        return new_id

    def increment_nozzle_slot_hours(self, position: str, value: float) -> None:
        """Increment hours on the active pool slot for this position."""
        pool = self.get_nozzle_pool()
        active = self.get_active_nozzle_slot(position)
        if active in pool:
            pool[active]["hours"] = pool[active].get("hours", 0.0) + value

    def get_active_nozzle_slot_hours(self, position: str = "single") -> float:
        pool = self.get_nozzle_pool()
        active = self.get_active_nozzle_slot(position)
        return float(pool.get(active, {}).get("hours", 0.0))

    def reset_nozzle_slot_hours(self, position: str) -> None:
        """Reset hours of the active pool slot to 0."""
        pool = self.get_nozzle_pool()
        active = self.get_active_nozzle_slot(position)
        if active in pool:
            pool[active]["hours"] = 0.0

    def rename_nozzle_slot(self, position: str, slot_id: str, new_label: str) -> None:
        """Rename a specific slot in the shared pool."""
        pool = self.get_nozzle_pool()
        if slot_id in pool:
            pool[slot_id]["label"] = new_label

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
