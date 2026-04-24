"""Frontend registration – registers the Bambu Companion JS cards as Lovelace resources."""
from __future__ import annotations

import logging
import pathlib

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import BAMBU_COMPANION_CARDS, URL_BASE

_LOGGER = logging.getLogger(__name__)


class BambuCompanionCardRegistration:
    """Registers & unregisters Bambu Companion JS cards as Lovelace module resources."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _resources(self):
        """Return the Lovelace resource collection (supports HA ≥ 2024.11)."""
        lovelace = self.hass.data.get("lovelace")
        if lovelace is None:
            return None
        # HA 2026.2+: lovelace is an object with .resources attribute
        if hasattr(lovelace, "resources"):
            return lovelace.resources
        # HA 2024.11–2026.1: lovelace is a dict
        if isinstance(lovelace, dict):
            return lovelace.get("resources")
        return None

    @property
    def _resource_mode(self) -> str:
        """Return 'storage' or 'yaml'."""
        lovelace = self.hass.data.get("lovelace")
        if lovelace is None:
            return "storage"
        if hasattr(lovelace, "resource_mode"):
            return lovelace.resource_mode
        if isinstance(lovelace, dict):
            return lovelace.get("mode", "storage")
        return "storage"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def async_register(self) -> None:
        """Register static file path and Lovelace module resources."""
        # 1. Serve the JS file via HA's HTTP server
        try:
            await self.hass.http.async_register_static_paths([
                StaticPathConfig(
                    URL_BASE,
                    str(pathlib.Path(__file__).parent),
                    False,
                )
            ])
            _LOGGER.debug("Bambu Companion: static path registered at %s", URL_BASE)
        except RuntimeError:
            _LOGGER.debug("Bambu Companion: static path already registered")

        # 2. YAML mode: can't add resources programmatically
        if self._resource_mode == "yaml":
            _LOGGER.warning(
                "Bambu Companion: Lovelace is in YAML mode – add the resource manually:\n"
                "  url: %s/bambu-companion-cards.js?v=%s\n  type: module",
                URL_BASE,
                BAMBU_COMPANION_CARDS[0]["version"],
            )
            return

        resources = self._resources
        if resources is None:
            _LOGGER.warning("Bambu Companion: could not access Lovelace resources")
            return

        if resources.loaded:
            await self._async_register_cards(resources)
        else:
            from homeassistant.helpers.event import async_call_later

            async def _check(now):  # type: ignore[no-untyped-def]
                r = self._resources
                if r is not None and r.loaded:
                    await self._async_register_cards(r)
                else:
                    _LOGGER.debug("Bambu Companion: Lovelace resources not ready, retrying in 5 s")
                    async_call_later(self.hass, 5, _check)

            async_call_later(self.hass, 1, _check)

    async def async_unregister(self) -> None:
        """Remove Bambu Companion Lovelace resources."""
        resources = self._resources
        if resources is None or not resources.loaded:
            return
        for card in BAMBU_COMPANION_CARDS:
            url_base = f"{URL_BASE}/{card['filename']}"
            for resource in list(resources.async_items()):
                if resource["url"].split("?")[0] == url_base:
                    await resources.async_delete_item(resource["id"])
                    _LOGGER.debug("Bambu Companion: unregistered %s", card["name"])

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _async_register_cards(self, resources) -> None:
        """Add or update each card JS file in Lovelace resources."""
        by_path = {
            r["url"].split("?")[0]: r
            for r in resources.async_items()
        }
        for card in BAMBU_COMPANION_CARDS:
            url       = f"{URL_BASE}/{card['filename']}"
            versioned = f"{url}?v={card['version']}"
            if url in by_path:
                if by_path[url]["url"] != versioned:
                    _LOGGER.debug("Bambu Companion: updating %s → v%s", card["name"], card["version"])
                    await resources.async_update_item(
                        by_path[url]["id"],
                        {"res_type": "module", "url": versioned},
                    )
                else:
                    _LOGGER.debug("Bambu Companion: %s already current (v%s)", card["name"], card["version"])
            else:
                _LOGGER.debug("Bambu Companion: registering %s v%s", card["name"], card["version"])
                await resources.async_create_item({"res_type": "module", "url": versioned})
