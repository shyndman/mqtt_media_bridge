from __future__ import annotations

import asyncio
import importlib.util
import sys
from dataclasses import dataclass
from enum import IntFlag, StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any

import voluptuous as vol

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = REPO_ROOT / "custom_components" / "mqtt_media_bridge"
CONST_PATH = COMPONENT_ROOT / "const.py"
MEDIA_PLAYER_PATH = COMPONENT_ROOT / "media_player.py"


class MediaPlayerEntityFeature(IntFlag):
    PAUSE = 1
    SEEK = 2
    VOLUME_SET = 4
    VOLUME_MUTE = 8
    PREVIOUS_TRACK = 16
    NEXT_TRACK = 32
    PLAY = 64
    STOP = 128
    SHUFFLE_SET = 256
    REPEAT_SET = 512


class MediaPlayerState(StrEnum):
    OFF = "off"
    ON = "on"
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"


class RepeatMode(StrEnum):
    ALL = "all"
    OFF = "off"
    ONE = "one"


@dataclass(slots=True)
class ReceiveMessage:
    topic: str
    payload: bytes


class MqttEntity:
    pass


class MediaPlayerEntity:
    pass


class ConfigEntry:
    entry_id: str
    data: dict[str, Any]


class HomeAssistant:
    pass


def callback(func):
    return func


class _SchemaContainer:
    schema: dict[str, Any] = {}


def _install_homeassistant_stubs() -> None:
    homeassistant = ModuleType("homeassistant")
    components = ModuleType("homeassistant.components")
    media_player_component = ModuleType("homeassistant.components.media_player")
    media_player_component.ENTITY_ID_FORMAT = "media_player.{}"
    media_player_component.MediaPlayerEntity = MediaPlayerEntity
    mqtt_component = ModuleType("homeassistant.components.mqtt")
    mqtt_component.CONF_STATE_TOPIC = "state_topic"
    mqtt_component.async_wait_for_mqtt_client = lambda hass: True
    media_player_const = ModuleType("homeassistant.components.media_player.const")
    media_player_const.DOMAIN = "media_player"
    media_player_const.MediaPlayerEntityFeature = MediaPlayerEntityFeature
    media_player_const.MediaPlayerState = MediaPlayerState
    media_player_const.RepeatMode = RepeatMode
    mqtt_config = ModuleType("homeassistant.components.mqtt.config")
    mqtt_config.MQTT_RO_SCHEMA = vol.Schema({})
    mqtt_const = ModuleType("homeassistant.components.mqtt.const")
    mqtt_const.ATTR_DISCOVERY_HASH = "discovery_hash"
    mqtt_const.ATTR_DISCOVERY_PAYLOAD = "discovery_payload"
    mqtt_const.ATTR_DISCOVERY_TOPIC = "discovery_topic"
    mqtt_entity = ModuleType("homeassistant.components.mqtt.entity")
    mqtt_entity.MqttEntity = MqttEntity
    mqtt_models = ModuleType("homeassistant.components.mqtt.models")
    mqtt_models.ReceiveMessage = ReceiveMessage
    mqtt_schemas = ModuleType("homeassistant.components.mqtt.schemas")
    mqtt_schemas.MQTT_ENTITY_COMMON_SCHEMA = _SchemaContainer()
    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = ConfigEntry
    core = ModuleType("homeassistant.core")
    core.HomeAssistant = HomeAssistant
    core.callback = callback
    helpers = ModuleType("homeassistant.helpers")
    config_validation = ModuleType("homeassistant.helpers.config_validation")
    config_validation.string = str
    entity_platform = ModuleType("homeassistant.helpers.entity_platform")
    entity_platform.AddConfigEntryEntitiesCallback = Any
    helpers_typing = ModuleType("homeassistant.helpers.typing")
    helpers_typing.ConfigType = dict[str, Any]
    helpers_typing.DiscoveryInfoType = dict[str, Any]
    ha_const = ModuleType("homeassistant.const")
    ha_const.STATE_UNAVAILABLE = "unavailable"
    ha_const.STATE_UNKNOWN = "unknown"
    util = ModuleType("homeassistant.util")
    util_dt = ModuleType("homeassistant.util.dt")
    util_dt.utcnow = lambda: "utcnow"

    sys.modules[homeassistant.__name__] = homeassistant
    sys.modules[components.__name__] = components
    sys.modules[media_player_component.__name__] = media_player_component
    sys.modules[mqtt_component.__name__] = mqtt_component
    sys.modules[media_player_const.__name__] = media_player_const
    sys.modules[mqtt_config.__name__] = mqtt_config
    sys.modules[mqtt_const.__name__] = mqtt_const
    sys.modules[mqtt_entity.__name__] = mqtt_entity
    sys.modules[mqtt_models.__name__] = mqtt_models
    sys.modules[mqtt_schemas.__name__] = mqtt_schemas
    sys.modules[config_entries.__name__] = config_entries
    sys.modules[core.__name__] = core
    sys.modules[helpers.__name__] = helpers
    sys.modules[config_validation.__name__] = config_validation
    sys.modules[entity_platform.__name__] = entity_platform
    sys.modules[helpers_typing.__name__] = helpers_typing
    sys.modules[ha_const.__name__] = ha_const
    sys.modules[util.__name__] = util
    sys.modules[util_dt.__name__] = util_dt

    custom_components = ModuleType("custom_components")
    custom_components.__path__ = [str(REPO_ROOT / "custom_components")]
    component_package = ModuleType("custom_components.mqtt_media_bridge")
    component_package.__path__ = [str(COMPONENT_ROOT)]
    sys.modules[custom_components.__name__] = custom_components
    sys.modules[component_package.__name__] = component_package


def _load_module(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_install_homeassistant_stubs()
CONST_MODULE = _load_module("custom_components.mqtt_media_bridge.const", CONST_PATH)
MEDIA_PLAYER_MODULE = _load_module("bridge_media_player_module", MEDIA_PLAYER_PATH)
MqttMediaPlayer = MEDIA_PLAYER_MODULE.MqttMediaPlayer


def _make_player(config: dict[str, str]) -> tuple[MqttMediaPlayer, dict[str, Any], list[str]]:
    player = object.__new__(MqttMediaPlayer)
    player._config = config
    player._mmb_entry_id = "entry-id"
    player.entity_id = "media_player.test"
    subscriptions: dict[str, Any] = {}
    writes: list[str] = []

    def add_subscription(key: str, callback: Any, _attrs: set[str]) -> bool:
        subscriptions[key] = callback
        return True

    player.add_subscription = add_subscription
    player.async_write_ha_state = lambda: writes.append("write")
    return player, subscriptions, writes


def test_config_schema_accepts_split_state_and_command_topics() -> None:
    schema = MqttMediaPlayer.config_schema()

    config = schema(
        {
            CONST_MODULE.CONF_VOLUME_MUTE_STATE_TOPIC: "bridge/player/volume_mute_state",
            CONST_MODULE.CONF_VOLUME_MUTE_COMMAND_TOPIC: "bridge/player/volume_mute",
            CONST_MODULE.CONF_SHUFFLE_STATE_TOPIC: "bridge/player/shuffle_state",
            CONST_MODULE.CONF_SHUFFLE_SET_TOPIC: "bridge/player/shuffle_set",
            CONST_MODULE.CONF_REPEAT_STATE_TOPIC: "bridge/player/repeat_state",
            CONST_MODULE.CONF_REPEAT_SET_TOPIC: "bridge/player/repeat_set",
        }
    )

    assert config[CONST_MODULE.CONF_VOLUME_MUTE_STATE_TOPIC].endswith("volume_mute_state")
    assert config[CONST_MODULE.CONF_VOLUME_MUTE_COMMAND_TOPIC].endswith("volume_mute")
    assert config[CONST_MODULE.CONF_SHUFFLE_STATE_TOPIC].endswith("shuffle_state")
    assert config[CONST_MODULE.CONF_SHUFFLE_SET_TOPIC].endswith("shuffle_set")
    assert config[CONST_MODULE.CONF_REPEAT_STATE_TOPIC].endswith("repeat_state")
    assert config[CONST_MODULE.CONF_REPEAT_SET_TOPIC].endswith("repeat_set")


def test_setup_from_config_enables_split_features() -> None:
    player, _subscriptions, _writes = _make_player(
        {
            CONST_MODULE.CONF_VOLUME_MUTE_COMMAND_TOPIC: "bridge/player/volume_mute",
            CONST_MODULE.CONF_SHUFFLE_SET_TOPIC: "bridge/player/shuffle_set",
            CONST_MODULE.CONF_REPEAT_SET_TOPIC: "bridge/player/repeat_set",
        }
    )

    player._setup_from_config(player._config)

    assert player._attr_supported_features & MediaPlayerEntityFeature.VOLUME_MUTE
    assert player._attr_supported_features & MediaPlayerEntityFeature.SHUFFLE_SET
    assert player._attr_supported_features & MediaPlayerEntityFeature.REPEAT_SET


def test_prepare_subscribe_topics_tracks_mute_shuffle_and_repeat_state() -> None:
    player, subscriptions, writes = _make_player(
        {
            CONST_MODULE.CONF_VOLUME_MUTE_STATE_TOPIC: "bridge/player/volume_mute_state",
            CONST_MODULE.CONF_SHUFFLE_STATE_TOPIC: "bridge/player/shuffle_state",
            CONST_MODULE.CONF_REPEAT_STATE_TOPIC: "bridge/player/repeat_state",
        }
    )

    player._prepare_subscribe_topics()

    subscriptions[CONST_MODULE.CONF_VOLUME_MUTE_STATE_TOPIC](
        ReceiveMessage("bridge/player/volume_mute_state", b"true")
    )
    subscriptions[CONST_MODULE.CONF_SHUFFLE_STATE_TOPIC](
        ReceiveMessage("bridge/player/shuffle_state", b"false")
    )
    subscriptions[CONST_MODULE.CONF_REPEAT_STATE_TOPIC](
        ReceiveMessage("bridge/player/repeat_state", b"all")
    )

    assert player._attr_is_volume_muted is True
    assert player._attr_shuffle is False
    assert player._attr_repeat is RepeatMode.ALL
    assert writes == ["write", "write", "write"]


def test_prepare_subscribe_topics_ignores_invalid_repeat_mode() -> None:
    player, subscriptions, writes = _make_player(
        {
            CONST_MODULE.CONF_REPEAT_STATE_TOPIC: "bridge/player/repeat_state",
        }
    )

    player._prepare_subscribe_topics()
    subscriptions[CONST_MODULE.CONF_REPEAT_STATE_TOPIC](
        ReceiveMessage("bridge/player/repeat_state", b"invalid")
    )

    assert not hasattr(player, "_attr_repeat")
    assert writes == []


def test_split_command_methods_publish_exact_topics_and_payloads() -> None:
    player, _subscriptions, _writes = _make_player(
        {
            CONST_MODULE.CONF_VOLUME_MUTE_COMMAND_TOPIC: "bridge/player/volume_mute",
            CONST_MODULE.CONF_SHUFFLE_SET_TOPIC: "bridge/player/shuffle_set",
            CONST_MODULE.CONF_REPEAT_SET_TOPIC: "bridge/player/repeat_set",
        }
    )
    publish_calls: list[tuple[str, str]] = []

    async def async_publish(topic: str, payload: str) -> None:
        publish_calls.append((topic, payload))

    player.async_publish = async_publish

    asyncio.run(player.async_mute_volume(True))
    asyncio.run(player.async_set_shuffle(False))
    asyncio.run(player.async_set_repeat(RepeatMode.ONE))

    assert publish_calls == [
        ("bridge/player/volume_mute", "true"),
        ("bridge/player/shuffle_set", "false"),
        ("bridge/player/repeat_set", "one"),
    ]
