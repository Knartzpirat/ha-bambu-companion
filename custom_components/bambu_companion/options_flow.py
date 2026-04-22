"""Options Flow for Bambu Print Tracker."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_CURRENCY,
    CONF_ELECTRICITY_PRICE,
    CONF_ELECTRICITY_SENSOR,
    CONF_ENERGY_SENSOR,
    CONF_FILAMENT_COST,
    CONF_FILAMENT_UNIT,
    CONF_LOW_FILAMENT_THRESHOLD,
    CONF_NOTIFY_INTERVAL,
    CONF_NOTIFY_ON_DONE,
    CONF_NOTIFY_ON_ERROR,
    CONF_NOTIFY_ON_LOW_FILAMENT,
    CONF_NOTIFY_ON_MAINTENANCE,
    CONF_NOTIFY_ON_PROGRESS,
    CONF_NOTIFY_ON_START,
    CONF_NOTIFY_TARGETS,
    CONF_PRINTER_DISPLAY_NAME,
    CONF_QUIET_FROM,
    CONF_QUIET_TO,
    DEFAULT_CURRENCY,
    DEFAULT_ELECTRICITY_PRICE,
    DEFAULT_FILAMENT_COST_PER_KG,
    DEFAULT_FILAMENT_UNIT,
    DEFAULT_LOW_FILAMENT_THRESHOLD,
    DEFAULT_NOTIFY_INTERVAL,
    DEFAULT_NOTIFY_ON_DONE,
    DEFAULT_NOTIFY_ON_ERROR,
    DEFAULT_NOTIFY_ON_LOW_FILAMENT,
    DEFAULT_NOTIFY_ON_MAINTENANCE,
    DEFAULT_NOTIFY_ON_PROGRESS,
    DEFAULT_NOTIFY_ON_START,
    DEFAULT_PRINTER_NAME,
    DEFAULT_QUIET_FROM,
    DEFAULT_QUIET_TO,
    MAINTENANCE_TASKS,
)


class BambuPrintTrackerOptionsFlow(config_entries.OptionsFlow):
    """Options flow – tabbed by step."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._combined: dict = {}

    def _current(self) -> dict:
        """Merged view: data values as base, options override."""
        return {**self.config_entry.data, **self.config_entry.options}

    async def async_step_init(self, user_input=None):
        """Show tab selection."""
        if user_input is not None:
            tab = user_input.get("tab")
            if tab == "energy":
                return await self.async_step_energy()
            if tab == "notify":
                return await self.async_step_notify()
            if tab == "maintenance":
                return await self.async_step_maintenance()
            if tab == "general":
                return await self.async_step_general()

        schema = vol.Schema(
            {
                vol.Required("tab", default="energy"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "energy", "label": "Kosten & Energie"},
                            {"value": "notify", "label": "Benachrichtigungen"},
                            {"value": "maintenance", "label": "Wartungspläne"},
                            {"value": "general", "label": "Allgemein"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_energy(self, user_input=None):
        current = self._current()
        if user_input is not None:
            self._combined.update(user_input)
            return self.async_create_entry(title="", data={**self.config_entry.options, **self._combined})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ELECTRICITY_PRICE,
                    default=current.get(CONF_ELECTRICITY_PRICE, DEFAULT_ELECTRICITY_PRICE),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0.0, max=10.0, step=0.01, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_ELECTRICITY_SENSOR,
                    description={"suggested_value": current.get(CONF_ELECTRICITY_SENSOR)},
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(
                    CONF_ENERGY_SENSOR,
                    description={"suggested_value": current.get(CONF_ENERGY_SENSOR)},
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_FILAMENT_COST,
                    default=current.get(CONF_FILAMENT_COST, DEFAULT_FILAMENT_COST_PER_KG),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0.0, max=1000.0, step=0.01, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_CURRENCY,
                    default=current.get(CONF_CURRENCY, DEFAULT_CURRENCY),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_FILAMENT_UNIT,
                    default=current.get(CONF_FILAMENT_UNIT, DEFAULT_FILAMENT_UNIT),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["kg", "g"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="energy", data_schema=schema)

    async def async_step_notify(self, user_input=None):
        current = self._current()
        if user_input is not None:
            self._combined.update(user_input)
            return self.async_create_entry(title="", data={**self.config_entry.options, **self._combined})

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NOTIFY_TARGETS,
                    description={"suggested_value": current.get(CONF_NOTIFY_TARGETS, [])},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[], multiple=True, custom_value=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_PRINTER_DISPLAY_NAME,
                    default=current.get(CONF_PRINTER_DISPLAY_NAME, DEFAULT_PRINTER_NAME),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_NOTIFY_INTERVAL,
                    default=current.get(CONF_NOTIFY_INTERVAL, DEFAULT_NOTIFY_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=50, step=1, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_QUIET_FROM,
                    default=current.get(CONF_QUIET_FROM, DEFAULT_QUIET_FROM),
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_QUIET_TO,
                    default=current.get(CONF_QUIET_TO, DEFAULT_QUIET_TO),
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_NOTIFY_ON_START,
                    default=current.get(CONF_NOTIFY_ON_START, DEFAULT_NOTIFY_ON_START),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_NOTIFY_ON_PROGRESS,
                    default=current.get(CONF_NOTIFY_ON_PROGRESS, DEFAULT_NOTIFY_ON_PROGRESS),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_NOTIFY_ON_DONE,
                    default=current.get(CONF_NOTIFY_ON_DONE, DEFAULT_NOTIFY_ON_DONE),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_NOTIFY_ON_ERROR,
                    default=current.get(CONF_NOTIFY_ON_ERROR, DEFAULT_NOTIFY_ON_ERROR),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_NOTIFY_ON_MAINTENANCE,
                    default=current.get(CONF_NOTIFY_ON_MAINTENANCE, DEFAULT_NOTIFY_ON_MAINTENANCE),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_NOTIFY_ON_LOW_FILAMENT,
                    default=current.get(CONF_NOTIFY_ON_LOW_FILAMENT, DEFAULT_NOTIFY_ON_LOW_FILAMENT),
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="notify", data_schema=schema)

    async def async_step_maintenance(self, user_input=None):
        current = self._current()
        if user_input is not None:
            intervals = dict(current.get("maintenance_intervals", {}))
            intervals.update(user_input)
            self._combined["maintenance_intervals"] = intervals
            return self.async_create_entry(title="", data={**self.config_entry.options, **self._combined})

        current_intervals = current.get("maintenance_intervals", {})
        fields = {}
        placeholders = {}
        for task in MAINTENANCE_TASKS:
            key = task["key"]
            default_val = current_intervals.get(key, task["default_interval"])
            fields[vol.Required(key, default=int(default_val))] = selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
            )
            placeholders[key] = task["name"]

        return self.async_show_form(
            step_id="maintenance",
            data_schema=vol.Schema(fields),
            description_placeholders=placeholders,
        )

    async def async_step_general(self, user_input=None):
        current = self._current()
        if user_input is not None:
            self._combined.update(user_input)
            return self.async_create_entry(title="", data={**self.config_entry.options, **self._combined})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_LOW_FILAMENT_THRESHOLD,
                    default=current.get(CONF_LOW_FILAMENT_THRESHOLD, DEFAULT_LOW_FILAMENT_THRESHOLD),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=50, step=1, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(step_id="general", data_schema=schema)



class BambuPrintTrackerOptionsFlow(config_entries.OptionsFlow):
    """Options flow – tabbed by step."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._combined: dict = {}

    async def async_step_init(self, user_input=None):
        """Show tab selection."""
        if user_input is not None:
            tab = user_input.get("tab")
            if tab == "energy":
                return await self.async_step_energy()
            if tab == "notify":
                return await self.async_step_notify()
            if tab == "texts":
                return await self.async_step_texts()
            if tab == "maintenance":
                return await self.async_step_maintenance()
            if tab == "general":
                return await self.async_step_general()

        schema = vol.Schema(
            {
                vol.Required("tab", default="energy"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "energy", "label": "Kosten & Energie"},
                            {"value": "notify", "label": "Benachrichtigungen"},
                            {"value": "texts", "label": "Texte anpassen"},
                            {"value": "maintenance", "label": "Wartungspläne"},
                            {"value": "general", "label": "Allgemein"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_energy(self, user_input=None):
        current = self.config_entry.options
        if user_input is not None:
            self._combined.update(user_input)
            return self.async_create_entry(title="", data={**current, **self._combined})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ELECTRICITY_PRICE,
                    default=current.get(CONF_ELECTRICITY_PRICE, DEFAULT_ELECTRICITY_PRICE),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0.0, max=10.0, step=0.01, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_ELECTRICITY_SENSOR,
                    description={"suggested_value": current.get(CONF_ELECTRICITY_SENSOR)},
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(
                    CONF_ENERGY_SENSOR,
                    description={"suggested_value": current.get(CONF_ENERGY_SENSOR)},
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_FILAMENT_COST,
                    default=current.get(CONF_FILAMENT_COST, DEFAULT_FILAMENT_COST_PER_KG),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0.0, max=1000.0, step=0.01, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_CURRENCY,
                    default=current.get(CONF_CURRENCY, DEFAULT_CURRENCY),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_FILAMENT_UNIT,
                    default=current.get(CONF_FILAMENT_UNIT, DEFAULT_FILAMENT_UNIT),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["kg", "g"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="energy", data_schema=schema)

    async def async_step_notify(self, user_input=None):
        current = self.config_entry.options
        if user_input is not None:
            self._combined.update(user_input)
            return self.async_create_entry(title="", data={**current, **self._combined})

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NOTIFY_TARGETS,
                    description={"suggested_value": current.get(CONF_NOTIFY_TARGETS, [])},
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[], multiple=True, custom_value=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_NOTIFY_INTERVAL,
                    default=current.get(CONF_NOTIFY_INTERVAL, DEFAULT_NOTIFY_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=50, step=1, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_QUIET_FROM,
                    default=current.get(CONF_QUIET_FROM, DEFAULT_QUIET_FROM),
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_QUIET_TO,
                    default=current.get(CONF_QUIET_TO, DEFAULT_QUIET_TO),
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_PRINTER_DISPLAY_NAME,
                    default=current.get(CONF_PRINTER_DISPLAY_NAME, DEFAULT_PRINTER_NAME),
                ): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="notify", data_schema=schema)

    async def async_step_texts(self, user_input=None):
        current = self.config_entry.options
        if user_input is not None:
            self._combined.update(user_input)
            return self.async_create_entry(title="", data={**current, **self._combined})

        def _text_field(key):
            return selector.TextSelector(selector.TextSelectorConfig(multiline=False))

        fields = {}
        for key in [
            CONF_TEXT_PROGRESS_TITLE, CONF_TEXT_DONE_TITLE, CONF_TEXT_ERROR_TITLE,
            CONF_TEXT_MAINT_TITLE, CONF_TEXT_RESET_TITLE,
            CONF_TEXT_PROGRESS_MSG, CONF_TEXT_DONE_MSG, CONF_TEXT_ERROR_MSG,
            CONF_TEXT_MAINT_MSG, CONF_TEXT_RESET_MSG,
            CONF_TEXT_BTN_DONE, CONF_TEXT_BTN_SNOOZE, CONF_TEXT_BTN_CANCEL,
            CONF_TEXT_BTN_RESET_CONFIRM, CONF_TEXT_BTN_RESET_CANCEL, CONF_TEXT_BTN_CAMERA,
        ]:
            fields[vol.Required(key, default=current.get(key, DEFAULT_TEXTS.get(key, "")))] = _text_field(key)

        return self.async_show_form(step_id="texts", data_schema=vol.Schema(fields))

    async def async_step_maintenance(self, user_input=None):
        current = self.config_entry.options
        if user_input is not None:
            intervals = current.get("maintenance_intervals", {})
            intervals.update(user_input)
            self._combined["maintenance_intervals"] = intervals
            return self.async_create_entry(title="", data={**current, **self._combined})

        current_intervals = current.get("maintenance_intervals", {})
        fields = {}
        for task in MAINTENANCE_TASKS:
            key = task["key"]
            default_val = current_intervals.get(key, task["default_interval"])
            fields[vol.Required(key, default=int(default_val))] = selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
            )

        return self.async_show_form(step_id="maintenance", data_schema=vol.Schema(fields))

    async def async_step_general(self, user_input=None):
        current = self.config_entry.options
        if user_input is not None:
            self._combined.update(user_input)
            return self.async_create_entry(title="", data={**current, **self._combined})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MAX_HISTORY,
                    default=current.get(CONF_MAX_HISTORY, DEFAULT_MAX_HISTORY),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=10, max=500, step=10, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_LOW_FILAMENT_THRESHOLD,
                    default=current.get(CONF_LOW_FILAMENT_THRESHOLD, DEFAULT_LOW_FILAMENT_THRESHOLD),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=50, step=1, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(step_id="general", data_schema=schema)
