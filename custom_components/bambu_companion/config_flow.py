"""Config Flow for Bambu Print Tracker."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_AMS_DEVICE_IDS,
    CONF_CURRENCY,
    CONF_DEVICE_ID,
    CONF_ELECTRICITY_PRICE,
    CONF_ELECTRICITY_SENSOR,
    CONF_ENERGY_SENSOR,
    CONF_FILAMENT_COST,
    CONF_FILAMENT_UNIT,
    CONF_NOTIFY_INTERVAL,
    CONF_NOTIFY_MOBILE_EVENTS,
    CONF_NOTIFY_HA_EVENTS,
    CONF_NOTIFY_TARGETS,
    CONF_PRINTER_DISPLAY_NAME,
    CONF_QUIET_FROM,
    CONF_QUIET_TO,
    DEFAULT_CURRENCY,
    DEFAULT_ELECTRICITY_PRICE,
    DEFAULT_FILAMENT_COST_PER_KG,
    DEFAULT_FILAMENT_UNIT,
    DEFAULT_NOTIFY_INTERVAL,
    DEFAULT_NOTIFY_MOBILE_EVENTS,
    DEFAULT_NOTIFY_HA_EVENTS,
    DEFAULT_QUIET_FROM,
    DEFAULT_QUIET_TO,
    DOMAIN,
)
from .entity_helper import get_ams_devices, get_bambu_devices
from .options_flow import BambuPrintTrackerOptionsFlow


class BambuPrintTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Bambu Print Tracker."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return BambuPrintTrackerOptionsFlow(config_entry)

    def __init__(self) -> None:
        self._data: dict = {}
        self._bambu_devices: list[dict] = []

    async def async_step_user(self, user_input=None):
        """Step 1: Select printer from bambu_lab devices."""
        errors: dict[str, str] = {}

        self._bambu_devices = await self.hass.async_add_executor_job(
            get_bambu_devices, self.hass
        )

        if not self._bambu_devices:
            return self.async_abort(reason="no_bambu_devices")

        device_options = {
            d["device_id"]: f"{d['name']} ({d['model']}, S/N: {d['serial']})"
            for d in self._bambu_devices
        }

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            selected = next(
                (d for d in self._bambu_devices if d["device_id"] == device_id), None
            )
            if selected is None:
                errors[CONF_DEVICE_ID] = "invalid_device"
            else:
                await self.async_set_unique_id(f"bc_{selected['serial']}")
                self._abort_if_unique_id_configured()
                self._data.update(
                    {
                        CONF_DEVICE_ID: device_id,
                        "serial": selected["serial"],
                        "model": selected["model"],
                        CONF_PRINTER_DISPLAY_NAME: selected["name"],
                    }
                )
                return await self.async_step_ams()

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": k, "label": v}
                            for k, v in device_options.items()
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_ams(self, user_input=None):
        """Step 2: Select AMS devices."""
        device_id = self._data[CONF_DEVICE_ID]
        ams_devices = await self.hass.async_add_executor_job(
            get_ams_devices, self.hass, device_id
        )

        if not ams_devices:
            # No AMS – skip this step
            self._data[CONF_AMS_DEVICE_IDS] = []
            return await self.async_step_energy()

        if user_input is not None:
            self._data[CONF_AMS_DEVICE_IDS] = user_input.get(CONF_AMS_DEVICE_IDS, [])
            return await self.async_step_energy()

        ams_options = [
            {"value": d["device_id"], "label": f"{d['name']} ({d['model']})"}
            for d in ams_devices
        ]
        default_ams = [d["device_id"] for d in ams_devices]

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_AMS_DEVICE_IDS, default=default_ams
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=ams_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )

        return self.async_show_form(step_id="ams", data_schema=schema)

    async def async_step_energy(self, user_input=None):
        """Step 3: Energy & cost configuration."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_notify()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ELECTRICITY_PRICE, default=DEFAULT_ELECTRICITY_PRICE
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=10.0, step=0.01, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_ELECTRICITY_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_ENERGY_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(
                    CONF_FILAMENT_COST, default=DEFAULT_FILAMENT_COST_PER_KG
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=1000.0, step=0.01, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_CURRENCY, default=DEFAULT_CURRENCY
                ): selector.TextSelector(),
                vol.Required(
                    CONF_FILAMENT_UNIT, default=DEFAULT_FILAMENT_UNIT
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
        """Step 4: Notification configuration."""
        if user_input is not None:
            self._data.update(user_input)
            title = self._data.get(CONF_PRINTER_DISPLAY_NAME, "Bambu Lab Printer")
            return self.async_create_entry(title=title, data=self._data)

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
        mobile_options.sort(key=lambda x: x["label"])

        schema = vol.Schema(
            {
                vol.Optional(CONF_NOTIFY_TARGETS): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=mobile_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_NOTIFY_INTERVAL, default=DEFAULT_NOTIFY_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=50, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_QUIET_FROM, default=DEFAULT_QUIET_FROM
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_QUIET_TO, default=DEFAULT_QUIET_TO
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_NOTIFY_MOBILE_EVENTS,
                    default=DEFAULT_NOTIFY_MOBILE_EVENTS,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "start", "label": "Druck gestartet"},
                            {"value": "progress", "label": "Fortschrittsupdate"},
                            {"value": "done", "label": "Druck abgeschlossen"},
                            {"value": "error", "label": "Druckfehler"},
                            {"value": "maintenance", "label": "Wartung fällig"},
                        ],
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_NOTIFY_HA_EVENTS,
                    default=DEFAULT_NOTIFY_HA_EVENTS,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "start", "label": "Druck gestartet"},
                            {"value": "progress", "label": "Fortschrittsupdate"},
                            {"value": "done", "label": "Druck abgeschlossen"},
                            {"value": "error", "label": "Druckfehler"},
                            {"value": "maintenance", "label": "Wartung fällig"},
                        ],
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="notify", data_schema=schema)
