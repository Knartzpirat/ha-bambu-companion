"""Maintenance plan logic for Bambu Print Tracker."""
from __future__ import annotations

from .const import MAINTENANCE_TASKS, PRINTER_FEATURES


def get_applicable_tasks(model: str, has_ams: bool) -> list[dict]:
    """Return maintenance tasks applicable for the given printer model."""
    features = PRINTER_FEATURES.get(model, {})
    applicable = []

    for task in MAINTENANCE_TASKS:
        allowed_models: list | None = task.get("models")
        requires_ams: bool = task.get("requires_ams", False)
        single_nozzle_only: bool = task.get("single_nozzle_only", False)

        if requires_ams and not has_ams:
            continue

        if single_nozzle_only and features.get("dual_nozzle", False):
            continue

        if allowed_models is not None and model not in allowed_models:
            continue

        applicable.append(task)

    return applicable


def is_maintenance_due(current_value: float, interval: float) -> bool:
    """Return True if the current value has reached or exceeded the interval."""
    return current_value >= interval


def format_maintenance_value(trigger: str, value: float) -> str:
    """Format a maintenance value for display."""
    if trigger in ("print_count", "laser_jobs"):
        return f"{int(value)} Drucke"
    return f"{value:.1f} h"
