"""Notification logic for Bambu Print Tracker."""
from __future__ import annotations

import logging
from datetime import datetime, time

from homeassistant.core import HomeAssistant

from .const import (
    CONF_NOTIFY_INTERVAL,
    CONF_NOTIFY_MOBILE_ENABLED,
    CONF_NOTIFY_HA_SUMMARY,
    CONF_NOTIFY_TARGETS,
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
    DEFAULT_NOTIFY_MOBILE_ENABLED,
    DEFAULT_NOTIFY_HA_SUMMARY,
    DEFAULT_TEXTS,
)

_LOGGER = logging.getLogger(__name__)


def _in_quiet_hours(quiet_from: str, quiet_to: str) -> bool:
    """Return True if current time is within quiet hours."""
    try:
        now = datetime.now().time()
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

    def __init__(self, hass: HomeAssistant, options: dict) -> None:
        self._hass = hass
        self._options = options
        self._last_notified_progress: int = -1

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

    async def _send(self, title: str, message: str) -> None:
        mobile_enabled = self._options.get(CONF_NOTIFY_MOBILE_ENABLED, DEFAULT_NOTIFY_MOBILE_ENABLED)
        targets = self._targets()
        if mobile_enabled and targets:
            if self._is_quiet():
                _LOGGER.debug("Suppressed mobile notification (quiet hours): %s", title)
            else:
                for target in targets:
                    try:
                        service_domain, service_name = target.rsplit(".", 1)
                        await self._hass.services.async_call(
                            service_domain,
                            service_name,
                            {"title": title, "message": message},
                            blocking=False,
                        )
                    except Exception as exc:  # noqa: BLE001
                        _LOGGER.warning("Failed to send notification to %s: %s", target, exc)

    def should_notify_progress(self, progress: int) -> bool:
        interval: int = int(self._options.get(CONF_NOTIFY_INTERVAL, 5))
        milestone = (progress // interval) * interval
        if milestone > self._last_notified_progress and progress > 0:
            self._last_notified_progress = milestone
            return True
        return False

    def reset_progress_tracker(self) -> None:
        self._last_notified_progress = -1

    async def notify_progress(self, variables: dict) -> None:
        title = _render(_get_text(self._options, CONF_TEXT_PROGRESS_TITLE), variables)
        message = _render(_get_text(self._options, CONF_TEXT_PROGRESS_MSG), variables)
        await self._send(title, message)

    async def notify_done(self, variables: dict) -> None:
        title = _render(_get_text(self._options, CONF_TEXT_DONE_TITLE), variables)
        message = _render(_get_text(self._options, CONF_TEXT_DONE_MSG), variables)
        await self._send(title, message)

    async def notify_error(self, variables: dict) -> None:
        title = _render(_get_text(self._options, CONF_TEXT_ERROR_TITLE), variables)
        message = _render(_get_text(self._options, CONF_TEXT_ERROR_MSG), variables)
        await self._send(title, message)

    async def notify_maintenance(self, variables: dict) -> None:
        title = _render(_get_text(self._options, CONF_TEXT_MAINT_TITLE), variables)
        message = _render(_get_text(self._options, CONF_TEXT_MAINT_MSG), variables)
        await self._send(title, message)

    async def notify_ha_summary(self, serial: str, variables: dict) -> None:
        """Create or update a persistent HA notification with the print summary."""
        if not self._options.get(CONF_NOTIFY_HA_SUMMARY, DEFAULT_NOTIFY_HA_SUMMARY):
            return
        from homeassistant.components.persistent_notification import async_create
        title = _render(_get_text(self._options, CONF_TEXT_DONE_TITLE), variables)
        message = _render(_get_text(self._options, CONF_TEXT_DONE_MSG), variables)
        async_create(
            self._hass,
            message,
            title=title,
            notification_id=f"bambu_companion_summary_{serial}",
        )
