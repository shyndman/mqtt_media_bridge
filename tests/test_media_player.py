from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
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
    TURN_ON = 128
    TURN_OFF = 256
    PLAY_MEDIA = 512
    VOLUME_STEP = 1024
    SELECT_SOURCE = 2048
    STOP = 4096
    PLAY = 16384
    SHUFFLE_SET = 32768
    SELECT_SOUND_MODE = 65536
    BROWSE_MEDIA = 131072
    REPEAT_SET = 262144


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


class _CachedAttr:
    """Mimic the HA CachedProperties `_attr_` semantics the bug relies on:
    reads default to None (so hasattr() is True) and deleting a never-set
    value raises AttributeError."""

    def __set_name__(self, owner: type, name: str) -> None:
        self._backing = f"_bk{name}"

    def __get__(self, obj: object, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        return getattr(obj, self._backing, None)

    def __set__(self, obj: object, value: Any) -> None:
        setattr(obj, self._backing, value)

    def __delete__(self, obj: object) -> None:
        delattr(obj, self._backing)


class MediaPlayerEntity:
    _attr_source_list = _CachedAttr()
    _attr_sound_mode_list = _CachedAttr()


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


def _make_player(
    config: dict[str, Any],
) -> tuple[MqttMediaPlayer, dict[str, Any], list[str]]:
    player = object.__new__(MqttMediaPlayer)
    player._config = config
    player._mmb_entry_id = "entry-id"
    player.entity_id = "media_player.test"
    player.hass = object()
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
            CONST_MODULE.CONF_SOURCE_LIST: ["TV", "Bluetooth"],
            CONST_MODULE.CONF_VOLUME_MUTE_STATE_TOPIC: "bridge/player/volume_mute_state",
            CONST_MODULE.CONF_VOLUME_MUTE_COMMAND_TOPIC: "bridge/player/volume_mute",
            CONST_MODULE.CONF_SHUFFLE_STATE_TOPIC: "bridge/player/shuffle_state",
            CONST_MODULE.CONF_SHUFFLE_SET_TOPIC: "bridge/player/shuffle_set",
            CONST_MODULE.CONF_REPEAT_STATE_TOPIC: "bridge/player/repeat_state",
            CONST_MODULE.CONF_REPEAT_SET_TOPIC: "bridge/player/repeat_set",
            CONST_MODULE.CONF_SOUND_MODE_LIST: ["Movie", "Music"],
            CONST_MODULE.CONF_SELECT_SOURCE_TOPIC: "bridge/player/select_source",
            CONST_MODULE.CONF_SELECT_SOUND_MODE_TOPIC: "bridge/player/select_sound_mode",
            CONST_MODULE.CONF_TURN_ON_TOPIC: "bridge/player/turn_on",
            CONST_MODULE.CONF_TURN_OFF_TOPIC: "bridge/player/turn_off",
            CONST_MODULE.CONF_PLAY_MEDIA_TOPIC: "bridge/player/play_media",
        }
    )

    assert config[CONST_MODULE.CONF_SOURCE_LIST] == ["TV", "Bluetooth"]
    assert config[CONST_MODULE.CONF_VOLUME_MUTE_STATE_TOPIC].endswith(
        "volume_mute_state"
    )
    assert config[CONST_MODULE.CONF_VOLUME_MUTE_COMMAND_TOPIC].endswith("volume_mute")
    assert config[CONST_MODULE.CONF_SHUFFLE_STATE_TOPIC].endswith("shuffle_state")
    assert config[CONST_MODULE.CONF_SHUFFLE_SET_TOPIC].endswith("shuffle_set")
    assert config[CONST_MODULE.CONF_REPEAT_STATE_TOPIC].endswith("repeat_state")
    assert config[CONST_MODULE.CONF_REPEAT_SET_TOPIC].endswith("repeat_set")
    assert config[CONST_MODULE.CONF_SOUND_MODE_LIST] == ["Movie", "Music"]
    assert config[CONST_MODULE.CONF_SELECT_SOURCE_TOPIC].endswith("select_source")
    assert config[CONST_MODULE.CONF_SELECT_SOUND_MODE_TOPIC].endswith(
        "select_sound_mode"
    )
    assert config[CONST_MODULE.CONF_TURN_ON_TOPIC].endswith("turn_on")
    assert config[CONST_MODULE.CONF_TURN_OFF_TOPIC].endswith("turn_off")
    assert config[CONST_MODULE.CONF_PLAY_MEDIA_TOPIC].endswith("play_media")


def test_setup_from_config_enables_split_features() -> None:
    player, _subscriptions, _writes = _make_player(
        {
            CONST_MODULE.CONF_SOURCE_LIST: ["TV", "Bluetooth"],
            CONST_MODULE.CONF_VOLUME_MUTE_COMMAND_TOPIC: "bridge/player/volume_mute",
            CONST_MODULE.CONF_SHUFFLE_SET_TOPIC: "bridge/player/shuffle_set",
            CONST_MODULE.CONF_REPEAT_SET_TOPIC: "bridge/player/repeat_set",
            CONST_MODULE.CONF_SOUND_MODE_LIST: ["Movie", "Music"],
            CONST_MODULE.CONF_SELECT_SOURCE_TOPIC: "bridge/player/select_source",
            CONST_MODULE.CONF_SELECT_SOUND_MODE_TOPIC: "bridge/player/select_sound_mode",
            CONST_MODULE.CONF_TURN_ON_TOPIC: "bridge/player/turn_on",
            CONST_MODULE.CONF_TURN_OFF_TOPIC: "bridge/player/turn_off",
            CONST_MODULE.CONF_PLAY_MEDIA_TOPIC: "bridge/player/play_media",
        }
    )

    player._setup_from_config(player._config)

    assert player._attr_source_list == ["TV", "Bluetooth"]
    assert player._attr_sound_mode_list == ["Movie", "Music"]
    assert player._attr_supported_features & MediaPlayerEntityFeature.SELECT_SOURCE
    assert player._attr_supported_features & MediaPlayerEntityFeature.SELECT_SOUND_MODE
    assert player._attr_supported_features & MediaPlayerEntityFeature.TURN_ON
    assert player._attr_supported_features & MediaPlayerEntityFeature.TURN_OFF
    assert player._attr_supported_features & MediaPlayerEntityFeature.PLAY_MEDIA
    assert player._attr_supported_features & MediaPlayerEntityFeature.VOLUME_MUTE
    assert player._attr_supported_features & MediaPlayerEntityFeature.SHUFFLE_SET
    assert player._attr_supported_features & MediaPlayerEntityFeature.REPEAT_SET


def test_setup_from_config_enables_volume_step_only_with_step_value() -> None:
    player, _subscriptions, _writes = _make_player(
        {
            CONST_MODULE.CONF_VOLUME_SET_TOPIC: "bridge/player/volume_set",
            CONST_MODULE.CONF_VOLUME_STEP: 0.1,
        }
    )

    player._setup_from_config(player._config)

    assert player._attr_supported_features & MediaPlayerEntityFeature.VOLUME_SET
    assert player._attr_supported_features & MediaPlayerEntityFeature.VOLUME_STEP
    assert player._attr_volume_step == 0.1


def test_setup_from_config_does_not_enable_volume_step_without_step_value() -> None:
    player, _subscriptions, _writes = _make_player(
        {
            CONST_MODULE.CONF_VOLUME_SET_TOPIC: "bridge/player/volume_set",
        }
    )

    player._setup_from_config(player._config)

    assert player._attr_supported_features & MediaPlayerEntityFeature.VOLUME_SET
    assert not player._attr_supported_features & MediaPlayerEntityFeature.VOLUME_STEP
    assert not hasattr(player, "_attr_volume_step")


def test_setup_from_config_without_lists_does_not_raise() -> None:
    player, _subscriptions, _writes = _make_player(
        {
            CONST_MODULE.CONF_PLAY_TOPIC: "bridge/player/play",
        }
    )

    player._setup_from_config(player._config)

    assert player._attr_source_list is None
    assert player._attr_sound_mode_list is None


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
            CONST_MODULE.CONF_PLAY_MEDIA_TOPIC: "bridge/player/play_media",
            CONST_MODULE.CONF_SELECT_SOURCE_TOPIC: "bridge/player/select_source",
            CONST_MODULE.CONF_SELECT_SOUND_MODE_TOPIC: "bridge/player/select_sound_mode",
            CONST_MODULE.CONF_TURN_ON_TOPIC: "bridge/player/turn_on",
            CONST_MODULE.CONF_TURN_OFF_TOPIC: "bridge/player/turn_off",
            CONST_MODULE.CONF_VOLUME_MUTE_COMMAND_TOPIC: "bridge/player/volume_mute",
            CONST_MODULE.CONF_SHUFFLE_SET_TOPIC: "bridge/player/shuffle_set",
            CONST_MODULE.CONF_REPEAT_SET_TOPIC: "bridge/player/repeat_set",
        }
    )
    publish_calls: list[tuple[str, str]] = []

    async def _record(hass, topic, payload="", *args, **kwargs) -> None:
        publish_calls.append((topic, payload))

    MEDIA_PLAYER_MODULE.mqtt.async_publish = _record

    asyncio.run(player.async_turn_on())
    asyncio.run(player.async_turn_off())
    asyncio.run(player.async_mute_volume(True))
    asyncio.run(
        player.async_play_media(
            "music",
            "track-123",
            enqueue="replace",
            announce=True,
        )
    )
    asyncio.run(player.async_select_source("Bluetooth"))
    asyncio.run(player.async_select_sound_mode("Movie"))
    asyncio.run(player.async_set_shuffle(False))
    asyncio.run(player.async_set_repeat(RepeatMode.ONE))

    play_media_payload = json.loads(publish_calls[3][1])

    assert publish_calls == [
        ("bridge/player/turn_on", ""),
        ("bridge/player/turn_off", ""),
        ("bridge/player/volume_mute", "ON"),
        ("bridge/player/play_media", publish_calls[3][1]),
        ("bridge/player/select_source", "Bluetooth"),
        ("bridge/player/select_sound_mode", "Movie"),
        ("bridge/player/shuffle_set", "OFF"),
        ("bridge/player/repeat_set", "one"),
    ]
    assert play_media_payload == {
        "media_type": "music",
        "media_id": "track-123",
        "enqueue": "replace",
        "announce": True,
    }


def test_decode_bool_payload_recognizes_and_warns(caplog) -> None:
    player, _subscriptions, _writes = _make_player({})

    assert player._decode_bool_payload("on") is True
    assert player._decode_bool_payload("off") is False
    assert player._decode_bool_payload("") is None
    assert player._decode_bool_payload(None) is None

    with caplog.at_level(logging.WARNING):
        assert player._decode_bool_payload("bogus") is None
    assert any(
        "Unexpected boolean payload" in record.getMessage() for record in caplog.records
    )
