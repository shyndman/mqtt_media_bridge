"""The Mellow MQTT Media Play (Mellow) integration."""

from __future__ import annotations

import logging

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Mellow MQTT Media component."""
    config_domains = list(config.keys()) if isinstance(config, dict) else []
    _LOGGER.debug("[m3p] async_setup invoked (config_domains=%s)", config_domains)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mellow MQTT Media from a config entry."""
    _LOGGER.debug(
        "[m3p] async_setup_entry start (entry_id=%s, title=%s, data_keys=%s)",
        entry.entry_id,
        entry.title,
        sorted(entry.data.keys()),
    )

    mqtt_ready = await mqtt.async_wait_for_mqtt_client(hass)
    if not mqtt_ready:
        _LOGGER.warning(
            "[m3p] MQTT client not ready, aborting setup for entry_id=%s",
            entry.entry_id,
        )
        return False
    _LOGGER.debug("[m3p] MQTT client ready for entry_id=%s", entry.entry_id)

    # Forward the entry setup to the media_player platform
    # Entity creation happens directly in media_player.async_setup_entry
    await hass.config_entries.async_forward_entry_setups(entry, ["media_player"])
    _LOGGER.debug(
        "[m3p] Entry forwarded to media_player platform (entry_id=%s)",
        entry.entry_id,
    )

    _LOGGER.debug("[m3p] async_setup_entry complete (entry_id=%s)", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("[m3p] async_unload_entry start (entry_id=%s)", entry.entry_id)

    # Note: We don't clean up mqtt_data.config here because:
    # 1. It's a shared MQTT structure
    # 2. The entity cleanup happens through the platform unload
    # 3. The MQTT integration manages its own config lifecycle

    unload_success = await hass.config_entries.async_unload_platforms(
        entry, ["media_player"]
    )
    _LOGGER.debug(
        "[m3p] async_unload_entry complete (entry_id=%s, success=%s)",
        entry.entry_id,
        unload_success,
    )
    return unload_success
