<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Repository Guidelines

## Project Structure & Module Organization
- Custom component code lives in `custom_components/mqtt_media_bridge/` (`__init__.py`, `media_player.py`, `entity.py`, `config_flow.py`, `const.py`, `manifest.json`). Treat this as the single source of Home Assistant integration logic.
- Local Home Assistant test configuration sits under `config/` (blueprints, temporary databases, `configuration.yaml`, `mosquitto.conf`). Use it when running the bundled dev instance.
- Helper scripts (`setup`, `develop`, `lint`) are in `scripts/`; they wrap environment bootstrapping, HA launch, and linting.
- Repository metadata—`requirements.txt`, `hacs.json`, `README.md`, and licensing—lives at the root for HACS compatibility.

## Build, Test & Development Commands
- `./scripts/setup` installs Python deps (see `requirements.txt`) and prepares the virtual environment.
- `./scripts/develop` launches the pinned Home Assistant version with the sample config; point your browser to the URL it prints to exercise flows end-to-end.
- `./scripts/lint` runs Ruff across `custom_components/mqtt_media_bridge`.
- When iterating manually, use Home Assistant’s MQTT panel plus `mosquitto_pub`/`mosquitto_sub` to simulate player state (`config/mosquitto.conf` shows the expected broker setup).

## Coding Style & Naming Conventions
- Python modules follow Home Assistant standards: 4-space indentation, snake_case functions, PascalCase classes, upper snake constants defined in `const.py`.
- Keep public strings and keys aligned with Home Assistant’s translation/domain expectations (domain name `mqtt_media_bridge`, config entry IDs, etc.).
- Ruff enforces formatting and lint rules; fix reported issues before opening a PR (`ruff --fix ...` is acceptable locally).

## Testing Guidelines
- No dedicated unit suite today; rely on `./scripts/develop` to validate behavior inside a live Home Assistant environment.
- Exercise discovery, config flow, and MQTT roundtrips (state + command topics) before submitting. Document any manual verification steps in your PR description.
- When adding new MQTT fields, update both the entity implementation and the README topic tables to match.

## Commit & Pull Request Guidelines
- Follow the existing short, imperative commit style (e.g., “Improve error handling, reduce duplication”). Reference issue numbers when relevant.
- PRs should spell out motivation, summarize validation (`./scripts/lint`, manual HA checks, MQTT payload captures), and attach screenshots/log snippets for UI or config-flow changes.
- Call out breaking changes to MQTT topic schemas or config options explicitly so downstream automations can be updated.

## Security & Configuration Tips
- Never commit real broker credentials or tokens; use sample values in docs and keep secrets in your local `.env` or HA secrets store.
- Confirm `config/mosquitto.conf` and `custom_components/mqtt_media_bridge/const.py` remain in sync regarding topic defaults and discovery prefixes.
