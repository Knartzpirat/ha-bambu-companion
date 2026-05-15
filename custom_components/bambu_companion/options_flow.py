"""Options Flow for Bambu Print Tracker."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_ACTION_BTN_1_TITLE,
    CONF_ACTION_BTN_1_URI,
    CONF_ACTION_BTN_2_CAMERA_TITLE,
    CONF_ACTION_BTN_2_FALLBACK_TITLE,
    CONF_ACTION_BTN_2_URI,
    CONF_ACTION_BTN_3_MODE,
    CONF_AUTO_POWEROFF_DELAY_MIN,
    CONF_AUTO_POWEROFF_DRY_MODE,
    CONF_AUTO_POWEROFF_ENABLED,
    CONF_AUTO_POWEROFF_SWITCH,
    CONF_CURRENCY,
    CONF_DEVICE_ID,
    CONF_ELECTRICITY_PRICE,
    CONF_ELECTRICITY_SENSOR,
    CONF_ENERGY_SENSOR,
    CONF_FILAMENT_COST,
    CONF_FILAMENT_UNIT,
    CONF_MAINTENANCE_DISABLED_TASKS,
    CONF_MAX_HISTORY,
    CONF_NOTIFY_HA_EVENTS,
    CONF_NOTIFY_INTERVAL,
    CONF_NOTIFY_MOBILE_EVENTS,
    CONF_NOTIFY_TARGETS,
    CONF_PRINTER_DISPLAY_NAME,
    CONF_QUIET_FROM,
    CONF_QUIET_TO,
    CONF_TEXT_BTN_CAMERA,
    CONF_TEXT_BTN_CANCEL,
    CONF_TEXT_BTN_DONE,
    CONF_TEXT_BTN_RESET_CANCEL,
    CONF_TEXT_BTN_RESET_CONFIRM,
    CONF_TEXT_BTN_SNOOZE,
    CONF_TEXT_DONE_MSG,
    CONF_TEXT_DONE_TITLE,
    CONF_TEXT_ERROR_MSG,
    CONF_TEXT_ERROR_TITLE,
    CONF_TEXT_MAINT_MSG,
    CONF_TEXT_MAINT_TITLE,
    CONF_TEXT_PROGRESS_MSG,
    CONF_TEXT_PROGRESS_TITLE,
    CONF_TEXT_RESET_MSG,
    CONF_TEXT_RESET_TITLE,
    CONF_TEXT_START_MSG,
    CONF_TEXT_START_TITLE,
    DEFAULT_AUTO_POWEROFF_DELAY_MIN,
    DEFAULT_AUTO_POWEROFF_DRY_MODE,
    DEFAULT_CURRENCY,
    DEFAULT_ELECTRICITY_PRICE,
    DEFAULT_FILAMENT_COST_PER_KG,
    DEFAULT_FILAMENT_UNIT,
    DEFAULT_MAX_HISTORY,
    DEFAULT_NOTIFY_INTERVAL,
    DEFAULT_NOTIFY_MOBILE_EVENTS,
    DEFAULT_NOTIFY_HA_EVENTS,
    DEFAULT_PRINTER_NAME,
    DEFAULT_QUIET_FROM,
    DEFAULT_QUIET_TO,
    DEFAULT_TEXTS,
    CONF_IMPORT_TOTAL_HOURS,
    MAINTENANCE_TASKS,
)
from .maintenance import get_applicable_tasks


class BambuPrintTrackerOptionsFlow(config_entries.OptionsFlow):
    """Options flow – tabbed by step."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._combined: dict = {}

    def _current(self) -> dict:
        """Merged view: data values as base, options override."""
        return {**self.config_entry.data, **self.config_entry.options}

    def _get_lovelace_uri_options(self) -> list[dict]:
        """Build URI options including all registered Lovelace dashboards from HA."""
        options = [
            {"value": "/", "label": "Home Assistant (/)"},
        ]
        try:
            lovelace = self.hass.data.get("lovelace")
            dashboards: dict | None = None
            if lovelace is not None:
                if hasattr(lovelace, "dashboards"):
                    dashboards = lovelace.dashboards
                elif isinstance(lovelace, dict):
                    dashboards = lovelace.get("dashboards")
            if dashboards:
                for url_path, dashboard in dashboards.items():
                    # url_path is None/'' for the default dashboard
                    nav_path = url_path if url_path else "lovelace"
                    title: str | None = None
                    if hasattr(dashboard, "config") and isinstance(dashboard.config, dict):
                        title = dashboard.config.get("title")
                    if not title and hasattr(dashboard, "title"):
                        title = dashboard.title
                    if not title and isinstance(dashboard, dict):
                        title = dashboard.get("title") or (dashboard.get("config") or {}).get("title")
                    uri = f"homeassistant://navigate/{nav_path}"
                    label = f"{title} ({uri})" if title else f"Lovelace: {nav_path} ({uri})"
                    options.append({"value": uri, "label": label})
            else:
                options.append({
                    "value": "homeassistant://navigate/lovelace/0",
                    "label": "HA Lovelace (homeassistant://navigate/lovelace/0)",
                })
        except Exception:
            options.append({
                "value": "homeassistant://navigate/lovelace/0",
                "label": "HA Lovelace (homeassistant://navigate/lovelace/0)",
            })
        options.append({"value": "app://bbl.intl.bambulab.com", "label": "Bambu App (app://bbl.intl.bambulab.com)"})
        return options

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
            if tab == "poweroff":
                return await self.async_step_poweroff()

        schema = vol.Schema(
            {
                vol.Required("tab", default="energy"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "energy", "label": "Costs & Energy"},
                            {"value": "notify", "label": "Notifications"},
                            {"value": "texts", "label": "Customize Texts"},
                            {"value": "maintenance", "label": "Maintenance Plans"},
                            {"value": "general", "label": "General"},
                            {"value": "poweroff", "label": "Auto-Poweroff"},
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
            # vol.Optional multi-selects return None when nothing is selected — normalise to []
            for key in (CONF_NOTIFY_MOBILE_EVENTS, CONF_NOTIFY_HA_EVENTS):
                if user_input.get(key) is None:
                    user_input[key] = []
            self._combined.update(user_input)
            return self.async_create_entry(title="", data={**self.config_entry.options, **self._combined})

        # Build list of HA Companion App devices (mobile_app integration only)
        mobile_options = []
        for entry in self.hass.config_entries.async_entries("mobile_app"):
            device_name = entry.data.get("device_name", "")
            if not device_name:
                continue
            slug = device_name.lower().replace(" ", "_").replace("-", "_")
            full_service = f"notify.mobile_app_{slug}"
            if f"mobile_app_{slug}" in self.hass.services.async_services().get("notify", {}):
                mobile_options.append({"value": full_service, "label": entry.title or device_name})
        # Keep already-saved targets that may not be in the list (e.g. old manual entries)
        saved_targets = current.get(CONF_NOTIFY_TARGETS, [])
        if isinstance(saved_targets, str):
            saved_targets = [saved_targets] if saved_targets else []
        existing_values = {o["value"] for o in mobile_options}
        for t in saved_targets:
            if t not in existing_values:
                mobile_options.append({"value": t, "label": t})
        mobile_options.sort(key=lambda x: x["label"])

        # Detect camera entity for this printer via entity_registry
        bambu_device_id = self.config_entry.data.get(CONF_DEVICE_ID, "")
        camera_entity_id: str | None = None
        if bambu_device_id:
            registry = er.async_get(self.hass)
            for entry in registry.entities.values():
                if entry.device_id == bambu_device_id and entry.domain == "camera":
                    camera_entity_id = entry.entity_id
                    break

        # Default suggested values – pre-fill when no value is saved yet
        default_btn1_title = current.get(CONF_ACTION_BTN_1_TITLE) or "📱 Bambu App"
        default_btn1_uri = current.get(CONF_ACTION_BTN_1_URI) or "app://bbl.intl.bambulab.com"
        default_btn2_camera_title = current.get(CONF_ACTION_BTN_2_CAMERA_TITLE) or "📷 Kamera"
        default_btn2_fallback_title = current.get(CONF_ACTION_BTN_2_FALLBACK_TITLE) or "🏠 Home Assistant"
        default_btn2_uri = current.get(CONF_ACTION_BTN_2_URI) or "/"
        default_btn3_mode = current.get(CONF_ACTION_BTN_3_MODE) or "off"

        schema_fields: dict = {
            vol.Required(
                CONF_PRINTER_DISPLAY_NAME,
                default=current.get(CONF_PRINTER_DISPLAY_NAME, DEFAULT_PRINTER_NAME),
            ): selector.TextSelector(),
            vol.Optional(
                CONF_NOTIFY_TARGETS,
                description={"suggested_value": saved_targets},
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=mobile_options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
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
            vol.Optional(
                CONF_NOTIFY_MOBILE_EVENTS,
                default=current.get(CONF_NOTIFY_MOBILE_EVENTS, DEFAULT_NOTIFY_MOBILE_EVENTS),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "start", "label": "Print started"},
                        {"value": "progress", "label": "Progress update"},
                        {"value": "done", "label": "Print complete"},
                        {"value": "error", "label": "Print failed"},
                        {"value": "maintenance", "label": "Maintenance due"},
                        {"value": "nozzle_change", "label": "Nozzle change detected"},
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Optional(
                CONF_NOTIFY_HA_EVENTS,
                default=current.get(CONF_NOTIFY_HA_EVENTS, DEFAULT_NOTIFY_HA_EVENTS),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "start", "label": "Print started"},
                        {"value": "done", "label": "Print complete"},
                        {"value": "error", "label": "Print failed"},
                        {"value": "maintenance", "label": "Maintenance due"},
                        {"value": "nozzle_change", "label": "Nozzle change detected"},
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Optional(
                CONF_ACTION_BTN_1_TITLE,
                description={"suggested_value": default_btn1_title},
            ): selector.TextSelector(),
            vol.Optional(
                CONF_ACTION_BTN_1_URI,
                description={"suggested_value": default_btn1_uri},
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "app://bbl.intl.bambulab.com", "label": "Bambu App (app://bbl.intl.bambulab.com)"},
                        {"value": "bambulab://", "label": "Bambu App alt (bambulab://)"},
                        {"value": "/", "label": "Home Assistant (/)"},
                    ],
                    custom_value=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_ACTION_BTN_2_CAMERA_TITLE,
                description={"suggested_value": default_btn2_camera_title},
            ): selector.TextSelector(),
            vol.Optional(
                CONF_ACTION_BTN_2_FALLBACK_TITLE,
                description={"suggested_value": default_btn2_fallback_title},
            ): selector.TextSelector(),
            vol.Optional(
                CONF_ACTION_BTN_2_URI,
                description={"suggested_value": default_btn2_uri},
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=self._get_lovelace_uri_options(),
                    custom_value=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_ACTION_BTN_3_MODE,
                description={"suggested_value": default_btn3_mode},
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "off", "label": "Aus / Off"},
                        {"value": "mute_progress", "label": "Stummschalten (Minuten-Eingabe) / Mute Progress"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }

        # description_placeholders for the step description
        camera_hint = (
            f"Erkannte Kamera-Entity: `{camera_entity_id}` – Taste 2 wird als Kamera-Button gesendet." if camera_entity_id
            else "⚠️ Kein Kamera-Entity gefunden – Taste 2 nutzt Fallback-URI."
        )

        return self.async_show_form(
            step_id="notify",
            data_schema=vol.Schema(schema_fields),
            description_placeholders={"camera_hint": camera_hint},
        )

    async def async_step_texts(self, user_input=None):
        current = self._current()
        if user_input is not None:
            self._combined.update(user_input)
            return self.async_create_entry(title="", data={**self.config_entry.options, **self._combined})

        def _text_field(key):
            return selector.TextSelector(selector.TextSelectorConfig(multiline=False))

        fields = {}
        for key in [
            CONF_TEXT_START_TITLE, CONF_TEXT_PROGRESS_TITLE, CONF_TEXT_DONE_TITLE, CONF_TEXT_ERROR_TITLE,
            CONF_TEXT_MAINT_TITLE, CONF_TEXT_RESET_TITLE,
            CONF_TEXT_START_MSG, CONF_TEXT_PROGRESS_MSG, CONF_TEXT_DONE_MSG, CONF_TEXT_ERROR_MSG,
            CONF_TEXT_MAINT_MSG, CONF_TEXT_RESET_MSG,
            CONF_TEXT_BTN_DONE, CONF_TEXT_BTN_SNOOZE, CONF_TEXT_BTN_CANCEL,
            CONF_TEXT_BTN_RESET_CONFIRM, CONF_TEXT_BTN_RESET_CANCEL, CONF_TEXT_BTN_CAMERA,
        ]:
            fields[vol.Required(key, default=current.get(key, DEFAULT_TEXTS.get(key, "")))] = _text_field(key)

        return self.async_show_form(step_id="texts", data_schema=vol.Schema(fields))

    async def async_step_maintenance(self, user_input=None):
        current = self._current()
        model = self.config_entry.data.get("model", "")
        has_ams = bool(self.config_entry.data.get("ams_device_ids", []))
        applicable_tasks = get_applicable_tasks(model, has_ams)

        if user_input is not None:
            disabled = []
            intervals = dict(current.get("maintenance_intervals", {}))
            for task in applicable_tasks:
                key = task["key"]
                if not user_input.get(key, True):
                    disabled.append(key)
                interval_val = user_input.get(f"interval_{key}")
                if interval_val is not None:
                    intervals[key] = int(interval_val)
            self._combined[CONF_MAINTENANCE_DISABLED_TASKS] = disabled
            self._combined["maintenance_intervals"] = intervals
            return self.async_create_entry(title="", data={**self.config_entry.options, **self._combined})

        current_intervals = current.get("maintenance_intervals", {})
        current_disabled = current.get(CONF_MAINTENANCE_DISABLED_TASKS, [])
        fields = {}

        for task in applicable_tasks:
            key = task["key"]
            # Enable toggle: True = task is active (not disabled)
            fields[vol.Required(key, default=(key not in current_disabled))] = selector.BooleanSelector()
            # Interval input
            default_val = current_intervals.get(key, task["default_interval"])
            fields[vol.Required(f"interval_{key}", default=int(default_val))] = selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
            )

        return self.async_show_form(
            step_id="maintenance",
            data_schema=vol.Schema(fields),
        )

    async def async_step_general(self, user_input=None):
        current = self._current()
        if user_input is not None:
            self._combined.update(user_input)
            return self.async_create_entry(title="", data={**self.config_entry.options, **self._combined})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MAX_HISTORY,
                    default=current.get(CONF_MAX_HISTORY, DEFAULT_MAX_HISTORY),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=500, step=10, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_IMPORT_TOTAL_HOURS,
                    default=current.get(CONF_IMPORT_TOTAL_HOURS, True),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_IMPORT_TOTAL_HOURS,
                    default=current.get(CONF_IMPORT_TOTAL_HOURS, True),
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="general", data_schema=schema)

    async def async_step_poweroff(self, user_input=None):
        current = self._current()
        if user_input is not None:
            self._combined.update(user_input)
            return self.async_create_entry(title="", data={**self.config_entry.options, **self._combined})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_AUTO_POWEROFF_ENABLED,
                    default=current.get(CONF_AUTO_POWEROFF_ENABLED, False),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_AUTO_POWEROFF_SWITCH,
                    description={"suggested_value": current.get(CONF_AUTO_POWEROFF_SWITCH)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["switch", "input_boolean"])
                ),
                vol.Required(
                    CONF_AUTO_POWEROFF_DELAY_MIN,
                    default=current.get(CONF_AUTO_POWEROFF_DELAY_MIN, DEFAULT_AUTO_POWEROFF_DELAY_MIN),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=480, step=1, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_AUTO_POWEROFF_DRY_MODE,
                    default=current.get(CONF_AUTO_POWEROFF_DRY_MODE, DEFAULT_AUTO_POWEROFF_DRY_MODE),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "ask", "label": "Fragen / Ask"},
                            {"value": "poweroff", "label": "Immer ausschalten / Always power off"},
                            {"value": "wait", "label": "Trocknung abwarten / Wait for drying"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="poweroff", data_schema=schema)
