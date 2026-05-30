"""Config flow for MQTT Media Bridge."""

from __future__ import annotations

import json
import logging

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MqttMediaPlayerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MQTT Media Bridge."""

    VERSION = 1

    def _summarize_payload(
        self, raw_payload: bytes | str | None, limit: int = 400
    ) -> str:
        """Generate a log-friendly payload preview."""

        if raw_payload in (None, ""):
            return "<empty payload>"

        if isinstance(raw_payload, bytes):
            try:
                raw_payload = raw_payload.decode("utf-8")
            except UnicodeDecodeError:
                return "<binary payload>"

        if len(raw_payload) <= limit:
            return raw_payload

        return f"{raw_payload[:limit]}...(truncated {len(raw_payload)} chars)"

    async def async_step_mqtt(
        self, discovery_info: MqttServiceInfo
    ) -> ConfigFlowResult:
        """Handle MQTT discovery."""
        payload_preview = self._summarize_payload(discovery_info.payload)
        _LOGGER.debug(
            "[mmb] MQTT discovery triggered (topic=%s, payload_preview=%s)",
            discovery_info.topic,
            payload_preview,
        )

        # Parse the discovery payload
        try:
            if not discovery_info.payload:
                # Empty payload means device removal
                _LOGGER.debug(
                    "[mmb] Empty discovery payload received for topic=%s",
                    discovery_info.topic,
                )
                for entry in self._async_current_entries():
                    if entry.data.get("discovery_topic") == discovery_info.topic:
                        _LOGGER.debug(
                            "[mmb] Removing config entry for topic=%s (entry_id=%s)",
                            discovery_info.topic,
                            entry.entry_id,
                        )
                        await self.hass.config_entries.async_remove(entry.entry_id)
                        return self.async_abort(reason="removed")
                return self.async_abort(reason="empty_payload")

            payload = json.loads(discovery_info.payload)
        except (json.JSONDecodeError, ValueError) as err:
            _LOGGER.debug(
                "[mmb] Invalid JSON in discovery payload (topic=%s, error=%s)",
                discovery_info.topic,
                err,
            )
            return self.async_abort(reason="invalid_payload")

        # Extract unique identifier from payload
        unique_id = payload.get("unique_id")
        if not unique_id:
            _LOGGER.debug(
                "[mmb] Discovery payload missing unique_id (topic=%s, keys=%s)",
                discovery_info.topic,
                sorted(payload.keys()),
            )
            return self.async_abort(reason="no_unique_id")

        _LOGGER.debug(
            "[mmb] Discovery payload accepted (topic=%s, unique_id=%s, name=%s, keys=%s)",
            discovery_info.topic,
            unique_id,
            payload.get("name"),
            sorted(payload.keys()),
        )

        # Use the unique_id as the config entry unique_id
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(
            updates={
                "discovery_topic": discovery_info.topic,
                "discovery_payload": payload,
            }
        )

        # Create device-specific config entry
        device_name = payload.get("name", "MQTT Media Bridge")
        if device_info := payload.get("device"):
            device_name = device_info.get("name", device_name)

        _LOGGER.debug(
            "[mmb] Creating/Updating config entry for unique_id=%s (device_name=%s, entry_title=%s)",
            unique_id,
            device_name,
            device_name,
        )

        return self.async_create_entry(
            title=device_name,
            data={
                "discovery_topic": discovery_info.topic,
                "discovery_payload": payload,
                "unique_id": unique_id,
            },
        )
