"""Notification logic for Bambu Print Tracker."""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from homeassistant.components.persistent_notification import async_create
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACTION_BTN_1_TITLE,
    CONF_ACTION_BTN_1_URI,
    CONF_ACTION_BTN_2_CAMERA_TITLE,
    CONF_ACTION_BTN_2_FALLBACK_TITLE,
    CONF_ACTION_BTN_2_URI,
    CONF_ACTION_BTN_3_MODE,
    CONF_NOTIFY_HA_EVENTS,
    CONF_NOTIFY_INTERVAL,
    CONF_NOTIFY_MOBILE_EVENTS,
    CONF_NOTIFY_TARGETS,
    CONF_QUIET_FROM,
    CONF_QUIET_TO,
    CONF_TEXT_BTN_CAMERA,
    CONF_TEXT_BTN_CANCEL,
    CONF_TEXT_BTN_DONE,
    CONF_TEXT_BTN_POWEROFF_AFTER_DRY,
    CONF_TEXT_BTN_POWEROFF_CANCEL,
    CONF_TEXT_BTN_POWEROFF_NOW,
    CONF_TEXT_POWEROFF_MSG,
    CONF_TEXT_POWEROFF_TITLE,
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
    CONF_TEXT_START_MSG,
    CONF_TEXT_START_TITLE,
    DEFAULT_NOTIFY_HA_EVENTS,
    DEFAULT_NOTIFY_MOBILE_EVENTS,
    DEFAULT_NOTIFY_HA_BOOLS,
    DEFAULT_NOTIFY_MOBILE_BOOLS,
    DEFAULT_TEXTS,
)

_LOGGER = logging.getLogger(__name__)


def _in_quiet_hours(quiet_from: str, quiet_to: str) -> bool:
    """Return True if current time is within quiet hours."""
    try:
        now = dt_util.now().time()
        t_from = time.fromisoformat(quiet_from)
        t_to = time.fromisoformat(quiet_to)

        if t_from <= t_to:
            return t_from <= now <= t_to
        # Overnight span (e.g. 22:00 – 07:00)
        return now >= t_from or now <= t_to
    except (ValueError, TypeError):
        return False


def _render(template: str, variables: dict) -> str:
    """Replace {variable} placeholders in a template string."""
    for key, value in variables.items():
        template = template.replace(f"{{{key}}}", str(value))
    return template


def _get_text(options: dict, key: str) -> str:
    return options.get(key, DEFAULT_TEXTS.get(key, ""))


class NotifyManager:
    """Handles all notification dispatching for one printer."""

    def __init__(self, hass: HomeAssistant, serial: str, options: dict, device_id: str = "") -> None:
        self._hass = hass
        self._serial = serial
        self._options = options
        self._device_id = device_id
        self._last_notified_progress: int = -1
        self._muted_until: datetime | None = None

    def mute_progress(self, minutes: int) -> None:
        """Mute progress notifications for the given number of minutes."""
        if minutes > 0:
            self._muted_until = dt_util.now() + timedelta(minutes=minutes)
            _LOGGER.info("[%s] Progress muted for %d min (until %s)", self._serial, minutes, self._muted_until)
        else:
            self._muted_until = None
            _LOGGER.info("[%s] Progress mute cleared", self._serial)

    def clear_mute(self) -> None:
        """Clear any active mute (e.g. when print finishes)."""
        self._muted_until = None

    def _is_muted(self) -> bool:
        """Return True when progress notifications are currently muted."""
        if self._muted_until is None:
            return False
        if dt_util.now() < self._muted_until:
            return True
        # Expired – auto-clear
        self._muted_until = None
        return False

    def _targets(self) -> list[str]:
        targets = self._options.get(CONF_NOTIFY_TARGETS, [])
        if isinstance(targets, str):
            return [targets] if targets else []
        return list(targets)

    def _is_quiet(self) -> bool:
        return _in_quiet_hours(
            self._options.get(CONF_QUIET_FROM, "22:00"),
            self._options.get(CONF_QUIET_TO, "07:00"),
        )

    def _get_mobile_events(self) -> list[str]:
        """Return enabled mobile event keys. Supports new bool format and legacy list format."""
        opts = self._options
        # New format: individual boolean keys
        if any(f"notify_mobile_{e}" in opts for e in ("start", "done", "error")):
            return [
                ev for ev in ["start", "progress", "done", "error", "maintenance", "nozzle_change"]
                if opts.get(f"notify_mobile_{ev}", DEFAULT_NOTIFY_MOBILE_BOOLS.get(f"notify_mobile_{ev}", False))
            ]
        # Legacy list format
        return opts.get(CONF_NOTIFY_MOBILE_EVENTS, DEFAULT_NOTIFY_MOBILE_EVENTS)

    def _get_ha_events(self) -> list[str]:
        """Return enabled HA notification event keys. Supports new bool format and legacy list format."""
        opts = self._options
        # New format: individual boolean keys
        if any(f"notify_ha_{e}" in opts for e in ("done", "error", "maintenance")):
            return [
                ev for ev in ["done", "error", "maintenance", "nozzle_change"]
                if opts.get(f"notify_ha_{ev}", DEFAULT_NOTIFY_HA_BOOLS.get(f"notify_ha_{ev}", False))
            ]
        # Legacy list format
        return opts.get(CONF_NOTIFY_HA_EVENTS, DEFAULT_NOTIFY_HA_EVENTS)

    def _camera_entity_id(self) -> str | None:
        """Return the camera entity_id for this printer's device, if any."""
        if not self._device_id:
            return None
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(self._hass)
        for entry in registry.entities.values():
            if entry.device_id == self._device_id and entry.domain == "camera":
                return entry.entity_id
        return None

    def _build_action_buttons(self) -> list[dict]:
        """Build action button list for mobile push notifications from config."""
        buttons = []

        # Button 1: configurable title + URI
        btn1_title = (self._options.get(CONF_ACTION_BTN_1_TITLE) or "").strip()
        btn1_uri = (self._options.get(CONF_ACTION_BTN_1_URI) or "").strip()
        if btn1_title and btn1_uri:
            buttons.append({"action": "URI", "title": btn1_title, "uri": btn1_uri})

        # Button 2: camera (auto-uri) when available, otherwise fallback URI
        camera_eid = self._camera_entity_id()
        if camera_eid:
            btn2_title = (self._options.get(CONF_ACTION_BTN_2_CAMERA_TITLE) or "").strip() or "📷 Kamera"
            buttons.append({"action": "URI", "title": btn2_title, "uri": f"entityId:{camera_eid}"})
        else:
            btn2_fallback_title = (self._options.get(CONF_ACTION_BTN_2_FALLBACK_TITLE) or "").strip()
            btn2_fallback_uri = (self._options.get(CONF_ACTION_BTN_2_URI) or "").strip()
            if btn2_fallback_title and btn2_fallback_uri:
                buttons.append({"action": "URI", "title": btn2_fallback_title, "uri": btn2_fallback_uri})

        # Button 3: mute progress (textInput behavior on iOS/Android)
        btn3_mode = (self._options.get(CONF_ACTION_BTN_3_MODE) or "off").strip()
        if btn3_mode == "mute_progress":
            mute_action = f"bc_mute_progress_{self._serial}"
            buttons.append({
                "action": mute_action,
                "title": "🔇 Stummschalten",
                "behavior": "textInput",
                "textInputButtonTitle": "Stummschalten",
                "textInputPlaceholder": "Minuten (z.B. 60)",
            })

        return buttons

    async def _send(self, event_key: str, title: str, message: str, extra_data: dict | None = None) -> None:
        """Route notification to configured channels based on per-event settings."""
        mobile_events = self._get_mobile_events()
        ha_events = self._get_ha_events()
        targets = self._targets()

        _LOGGER.info(
            "[%s] _send(%s): mobile_events=%s ha_events=%s targets=%s quiet=%s",
            self._serial, event_key, mobile_events, ha_events, targets, self._is_quiet(),
        )

        # --- Mobile channel ---
        if event_key in mobile_events:
            if targets:
                if self._is_quiet():
                    _LOGGER.info("[%s] Suppressed mobile push (quiet hours): %s", self._serial, title)
                else:
                    action_buttons = self._build_action_buttons()
                    for target in targets:
                        try:
                            service_domain, service_name = target.rsplit(".", 1)
                            _LOGGER.info("[%s] Sending mobile push to %s: %s", self._serial, target, title)
                            service_data: dict = {"title": title, "message": message}
                            push_data: dict = {}
                            if extra_data:
                                push_data.update(extra_data)
                            if action_buttons:
                                push_data["actions"] = action_buttons
                            if push_data:
                                service_data["data"] = push_data
                            await self._hass.services.async_call(
                                service_domain,
                                service_name,
                                service_data,
                                blocking=False,
                            )
                        except Exception as exc:  # noqa: BLE001
                            _LOGGER.warning("[%s] Failed to send notification to %s: %s", self._serial, target, exc)
            else:
                _LOGGER.info("[%s] Event '%s' in mobile_events but NO targets configured", self._serial, event_key)
        else:
            _LOGGER.info("[%s] Event '%s' NOT in mobile_events — skipping mobile push", self._serial, event_key)

        # --- HA persistent notification channel ---
        if event_key in ha_events:
            _LOGGER.info("[%s] Creating HA persistent notification for event '%s'", self._serial, event_key)
            async_create(
                self._hass,
                message,
                title=title,
                notification_id=f"bambu_companion_{self._serial}_{event_key}",
            )
        else:
            _LOGGER.info("[%s] Event '%s' NOT in ha_events — skipping HA notification", self._serial, event_key)

    def should_notify_progress(self, progress: int) -> bool:
        interval: int = int(self._options.get(CONF_NOTIFY_INTERVAL, 5))
        milestone = (progress // interval) * interval
        if milestone > self._last_notified_progress and progress > 0:
            self._last_notified_progress = milestone
            return True
        return False

    def reset_progress_tracker(self) -> None:
        self._last_notified_progress = -1

    async def notify_start(self, variables: dict) -> None:
        title = _render(_get_text(self._options, CONF_TEXT_START_TITLE), variables)
        message = _render(_get_text(self._options, CONF_TEXT_START_MSG), variables)
        await self._send("start", title, message)

    async def notify_progress(self, variables: dict) -> None:
        if self._is_muted():
            _LOGGER.info("[%s] Progress notification suppressed (muted until %s)", self._serial, self._muted_until)
            return
        title = _render(_get_text(self._options, CONF_TEXT_PROGRESS_TITLE), variables)
        message = _render(_get_text(self._options, CONF_TEXT_PROGRESS_MSG), variables)
        await self._send("progress", title, message)

    async def notify_done(self, variables: dict) -> None:
        title = _render(_get_text(self._options, CONF_TEXT_DONE_TITLE), variables)
        message = _render(_get_text(self._options, CONF_TEXT_DONE_MSG), variables)
        await self._send("done", title, message)

    async def notify_poweroff_ask(self, printer_name: str) -> None:
        """Send a push notification asking the user whether to power off or wait for AMS drying."""
        targets = self._targets()
        if not targets:
            return
        if self._is_quiet():
            _LOGGER.info("[%s] Poweroff question suppressed (quiet hours)", self._serial)
            return

        title = _render(_get_text(self._options, CONF_TEXT_POWEROFF_TITLE), {"drucker": printer_name})
        message = _get_text(self._options, CONF_TEXT_POWEROFF_MSG)
        action_buttons = [
            {"action": f"bc_poweroff_now_{self._serial}", "title": _get_text(self._options, CONF_TEXT_BTN_POWEROFF_NOW)},
            {"action": f"bc_poweroff_after_dry_{self._serial}", "title": _get_text(self._options, CONF_TEXT_BTN_POWEROFF_AFTER_DRY)},
            {"action": f"bc_poweroff_wait_{self._serial}", "title": _get_text(self._options, CONF_TEXT_BTN_POWEROFF_CANCEL)},
        ]

        for target in targets:
            try:
                service_domain, service_name = target.rsplit(".", 1)
                await self._hass.services.async_call(
                    service_domain,
                    service_name,
                    {
                        "title": title,
                        "message": message,
                        "data": {"actions": action_buttons},
                    },
                    blocking=False,
                )
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("[%s] Failed to send poweroff question to %s: %s", self._serial, target, exc)

    async def notify_error(self, variables: dict) -> None:
        title = _render(_get_text(self._options, CONF_TEXT_ERROR_TITLE), variables)
        message = _render(_get_text(self._options, CONF_TEXT_ERROR_MSG), variables)
        await self._send("error", title, message)

    async def notify_maintenance(self, variables: dict) -> None:
        title = _render(_get_text(self._options, CONF_TEXT_MAINT_TITLE), variables)
        message = _render(_get_text(self._options, CONF_TEXT_MAINT_MSG), variables)
        await self._send("maintenance", title, message)

    async def notify_nozzle_change(self, variables: dict) -> None:
        """Notify the user that a nozzle change was detected and ask them to confirm the slot."""
        drucker = variables.get("drucker", "Drucker")
        serial = variables.get("serial", "")
        position = variables.get("position", "single")
        diameter = variables.get("diameter")
        nozzle_type = variables.get("nozzle_type", "")
        labels: list[str] = variables.get("labels", [])
        active = variables.get("active", "")

        diameter_str = f"{diameter:.2f} mm" if diameter else "?"
        type_str = f" ({nozzle_type})" if nozzle_type else ""
        title = f"🔧 {drucker} – Düsenwechsel erkannt"
        select_entity = f"select.bc_{serial}_nozzle_{position}"
        message = (
            f"Neue Düse erkannt: **{diameter_str}{type_str}**\n\n"
            f"Welche physische Düse ist jetzt eingebaut? "
            f"Bitte wähle den Slot über die Entität `{select_entity}` "
            f"oder tippe auf die passende Schaltfläche (aktiv: {active})."
        )

        mobile_events = self._get_mobile_events()
        ha_events = self._get_ha_events()

        # Mobile push with action buttons (one per slot)
        if "nozzle_change" in mobile_events:
            targets = self._targets()
            if targets and not self._is_quiet():
                action_buttons = [
                    {
                        "action": f"bc_nozzle_slot_{serial}_{position}_{label}",
                        "title": f"{'✅ ' if label == active else ''}{label}",
                    }
                    for label in labels
                ]
                for target in targets:
                    try:
                        service_domain, service_name = target.rsplit(".", 1)
                        await self._hass.services.async_call(
                            service_domain,
                            service_name,
                            {
                                "title": title,
                                "message": message,
                                "data": {
                                    "actions": action_buttons,
                                    "tag": f"bc_nozzle_change_{serial}_{position}",
                                },
                            },
                            blocking=False,
                        )
                    except Exception as exc:  # noqa: BLE001
                        _LOGGER.warning("Failed to send nozzle change notification to %s: %s", target, exc)

        # HA persistent notification
        if "nozzle_change" in ha_events:
            async_create(
                self._hass,
                message,
                title=title,
                notification_id=f"bambu_companion_{serial}_nozzle_change_{position}",
            )

