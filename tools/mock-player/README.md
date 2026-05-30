# Mock Player

A standalone CLI media player emulator for manual testing of the MQTT Media Bridge Home Assistant integration. It publishes MQTT discovery and state updates using `ha-mqtt-discoverable`, listens for command topics, and continuously plays fake tracks with PNG artwork.

## Quick start

1. Update `tools/.env` (uncommitted) to match your broker settings.
2. Run the tool:

```bash
scripts/mock-player
```

## Environment variables

`tools/.env.sample` contains defaults. `tools/.env` overrides are loaded at runtime.

- `MQTT_WS_URL` (default: `ws://ha-mosquitto-ws.don:80`)
- `MQTT_USERNAME` (optional)
- `MQTT_PASSWORD` (optional)
- `MQTT_CLIENT_NAME` (default: `mock-player`)
- `MQTT_DISCOVERY_PREFIX` (default: `homeassistant`)
- `MQTT_STATE_PREFIX` (default: `hmd`)
- `DEVICE_NAME` (default: `Mock Player`)
- `DEVICE_ID` (default: `mock-player`)
- `ENTITY_NAME` (default: `Mock Player`)
- `ENTITY_OBJECT_ID` (default: `mock_player`)
- `TICK_SECONDS` (default: `1`)
- `TRACK_DURATION_MIN_SECONDS` (default: `120`)
- `TRACK_DURATION_MAX_SECONDS` (default: `360`)
