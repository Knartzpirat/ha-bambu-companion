# ha-bambu-companion – Copilot Instructions

## Agent Permissions

The AI agent is **authorized to directly edit files** in this workspace without asking for confirmation.
This includes:
- Editing Python source files (`custom_components/bambu_companion/**/*.py`)
- Updating `manifest.json`, `const.py`, `strings.json`, translation files
- Modifying `CHANGELOG.md`
- Reading and writing `.github/prompts/` files

The agent should **implement changes directly** rather than only describing them.

## Project Context

Home Assistant custom integration for Bambu Lab printers.
- Language: Python 3.12+, follows Home Assistant integration patterns
- Key files: `coordinator.py`, `storage.py`, `notify.py`, `sensor.py`, `select.py`, `button.py`, `options_flow.py`, `config_flow.py`
- Dependency: `ha-bambulab` integration (entity lookup via `translation_key`)

## Conventions

- Version is tracked in `manifest.json` (`"version"`)
- Changelog format: Keep a Changelog (`CHANGELOG.md`) — prepend new entries
- Storage: HA `Store` via `storage.py`; persistent data survives HA restarts
- Notifications: `notify.py` dispatches both mobile push and HA persistent notifications
- Event config constants: `CONF_NOTIFY_MOBILE_EVENTS`, `CONF_NOTIFY_HA_EVENTS` in `const.py`
- HA events do **not** include `progress` (spam prevention); mobile events may include it

## Build & Reload

To test changes, reload the integration in HA: Developer Tools → YAML → Reload all custom integrations.
No build step required — Python files are used directly.
