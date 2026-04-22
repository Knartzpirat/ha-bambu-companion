"""Storage backend for Bambu Print Tracker print history."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

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
        """Reset a maintenance task counter to 0."""
        maint = self.get_maintenance()
        maint[task_key] = {
            "value": 0,
            "last_reset": datetime.now().isoformat(),
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

    def get_monthly_stats(self) -> dict:
        """Compute current-month stats from history."""
        now = datetime.now()
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
