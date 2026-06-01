from __future__ import annotations

import base64
import colorsys
import io
import logging
import os
import random
import signal
import threading
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
from PIL import Image, ImageDraw, ImageFont

from ha_mqtt_discoverable import DeviceInfo, Discoverable, Settings
from ha_mqtt_discoverable.media_player import (
    MediaPlayer,
    MediaPlayerCallbacks,
    MediaPlayerInfo,
)

LOGGER = logging.getLogger("mock_player")


@dataclass(frozen=True)
class Config:
    mqtt_ws_url: str
    mqtt_username: str | None
    mqtt_password: str | None
    mqtt_client_name: str
    mqtt_discovery_prefix: str
    mqtt_state_prefix: str
    device_name: str
    device_id: str
    entity_name: str
    entity_object_id: str
    tick_seconds: float
    track_duration_min_seconds: int
    track_duration_max_seconds: int


@dataclass
class Track:
    title: str
    artist: str
    album: str
    duration: int
    artwork_data_url: str


class WebSocketMediaPlayer(MediaPlayer):
    """MediaPlayer that ensures WebSocket clients subscribe on connect."""

    def __init__(
        self,
        settings: Settings[MediaPlayerInfo],
        callbacks: MediaPlayerCallbacks,
        user_data=None,
    ) -> None:
        LOGGER.debug(
            "Initializing WebSocketMediaPlayer with callbacks: %s",
            list(callbacks.keys()),
        )
        self._callbacks = callbacks
        self._topics = {}
        self._generate_topics(settings)

        Discoverable.__init__(self, settings, self._on_client_connected)

        self.mqtt_client.on_message = self._command_callback_handler
        # Ensure command subscriptions happen on connect for custom clients.
        self.mqtt_client.on_connect = self._on_client_connected
        self._connect_client()


class MockPlayer:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        self._state = "playing"
        self._position = 0.0
        self._volume = 0.5
        self._last_volume = self._volume
        self._muted = False
        self._track_index = 0
        self._current_track = self._generate_track(self._track_index)

        self._player = self._build_media_player()

        self._publish_track(self._current_track, reset_position=True)
        self._player.set_volume(self._volume)
        self._player.set_muted(self._muted)
        self._player.set_state(self._state)
        self._player.set_availability(True)

        self._start_loop()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        try:
            self._player.set_availability(False)
        except Exception:
            LOGGER.exception("Failed to set availability offline")
        try:
            self._player.mqtt_client.publish(self._player.config_topic, "", retain=True)
        except Exception:
            LOGGER.exception("Failed to publish discovery removal")
        try:
            self._player.mqtt_client.loop_stop()
            self._player.mqtt_client.disconnect()
        except Exception:
            LOGGER.exception("Failed to disconnect MQTT client")

    def _build_media_player(self) -> WebSocketMediaPlayer:
        ws_url = self._config.mqtt_ws_url
        host, port, path, use_tls = _parse_ws_url(ws_url)
        mqtt_client = mqtt.Client(
            client_id=self._config.mqtt_client_name,
            transport="websockets",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        mqtt_client.ws_set_options(path=path)
        if use_tls:
            mqtt_client.tls_set()
        if self._config.mqtt_username:
            mqtt_client.username_pw_set(
                self._config.mqtt_username, self._config.mqtt_password
            )

        mqtt_settings = Settings.MQTT(
            host=host,
            port=port,
            client_name=self._config.mqtt_client_name,
            discovery_prefix=self._config.mqtt_discovery_prefix,
            state_prefix=self._config.mqtt_state_prefix,
            client=mqtt_client,
        )

        device_info = DeviceInfo(
            name=self._config.device_name,
            identifiers=[self._config.device_id],
            manufacturer="Mock Player",
            model="Mock Media Device",
        )

        unique_id = f"{self._config.device_id}-{self._config.entity_object_id}"
        entity_info = MediaPlayerInfo(
            name=self._config.entity_name,
            object_id=self._config.entity_object_id,
            unique_id=unique_id,
            device=device_info,
        )

        callbacks: MediaPlayerCallbacks = {
            "play": self._on_play,
            "pause": self._on_pause,
            "stop": self._on_stop,
            "next_track": self._on_next_track,
            "previous_track": self._on_previous_track,
            "seek": self._on_seek,
            "volume_set": self._on_volume_set,
            "volume_mute": self._on_volume_mute,
        }

        settings = Settings(
            mqtt=mqtt_settings, entity=entity_info, manual_availability=True
        )
        player = WebSocketMediaPlayer(settings, callbacks)
        LOGGER.info("Connected to MQTT broker at %s:%s via WebSocket", host, port)
        return player

    def _start_loop(self) -> None:
        self._thread = threading.Thread(
            target=self._playback_loop, name="mock-player-loop", daemon=True
        )
        self._thread.start()

    def _playback_loop(self) -> None:
        tick = self._config.tick_seconds
        while not self._stop_event.wait(tick):
            with self._lock:
                if self._state != "playing":
                    continue
                self._position += tick
                if self._position >= self._current_track.duration:
                    self._advance_track(1, force_playing=True)
                    continue
                self._player.set_position(int(self._position))

    def _advance_track(self, delta: int, force_playing: bool) -> None:
        self._track_index = (self._track_index + delta) % 26
        self._current_track = self._generate_track(self._track_index)
        self._position = 0.0
        if force_playing:
            self._state = "playing"
            self._player.set_state("playing")
        self._publish_track(self._current_track, reset_position=True)

    def _publish_track(self, track: Track, reset_position: bool) -> None:
        self._player.set_title(track.title)
        self._player.set_artist(track.artist)
        self._player.set_album(track.album)
        self._player.set_duration(track.duration)
        self._player.set_albumart_url(track.artwork_data_url)
        self._player.set_media_image_remotely_accessible(True)
        if reset_position:
            self._player.set_position(0)

    def _generate_track(self, index: int) -> Track:
        letter = chr(ord("a") + (index % 26))
        title = letter * 3
        artist = f"Artist {letter.upper()}"
        album = f"Album {letter.upper()}"
        duration = random.randint(
            self._config.track_duration_min_seconds,
            self._config.track_duration_max_seconds,
        )
        artwork_data_url = _generate_png_data_url(title, index)
        return Track(
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            artwork_data_url=artwork_data_url,
        )

    def _on_play(self, client, user_data, message) -> None:
        with self._lock:
            self._state = "playing"
            self._player.set_state("playing")

    def _on_pause(self, client, user_data, message) -> None:
        with self._lock:
            self._state = "paused"
            self._player.set_state("paused")

    def _on_stop(self, client, user_data, message) -> None:
        with self._lock:
            self._state = "idle"
            self._position = 0.0
            self._player.set_state("idle")
            self._player.set_position(0)

    def _on_next_track(self, client, user_data, message) -> None:
        with self._lock:
            self._advance_track(1, force_playing=True)

    def _on_previous_track(self, client, user_data, message) -> None:
        with self._lock:
            self._advance_track(-1, force_playing=True)

    def _on_seek(self, position: float | None, client, user_data, message) -> None:
        if position is None:
            return
        with self._lock:
            clamped = max(0.0, min(position, float(self._current_track.duration)))
            self._position = clamped
            self._player.set_position(int(self._position))

    def _on_volume_set(self, volume: float | None, client, user_data, message) -> None:
        if volume is None:
            return
        clamped = max(0.0, min(volume, 1.0))
        with self._lock:
            self._volume = clamped
            if not self._muted:
                self._last_volume = clamped
            self._player.set_volume(self._volume)

    def _on_volume_mute(self, _value: bool | None, client, user_data, message) -> None:
        payload = message.payload.decode("utf-8").strip().lower()
        muted = payload in {"true", "1", "yes", "on"}
        with self._lock:
            if muted:
                self._muted = True
                self._last_volume = self._volume
                self._volume = 0.0
            else:
                self._muted = False
                self._volume = self._last_volume
            self._player.set_volume(self._volume)
            self._player.set_muted(self._muted)


def _generate_png_data_url(label: str, index: int) -> str:
    size = 512
    hue = (index * 37) % 360
    rgb = colorsys.hsv_to_rgb(hue / 360.0, 0.5, 0.9)
    background = tuple(int(channel * 255) for channel in rgb)

    image = Image.new("RGB", (size, size), background)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    text = label.upper()
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (size - text_width) / 2
    text_y = (size - text_height) / 2

    draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _parse_ws_url(url: str) -> tuple[str, int, str, bool]:
    parsed = urlparse(url)
    if parsed.scheme not in {"ws", "wss"}:
        raise ValueError(f"MQTT_WS_URL must start with ws:// or wss:// (got: {url})")
    if not parsed.hostname:
        raise ValueError(f"MQTT_WS_URL missing hostname: {url}")

    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "wss" else 80

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    use_tls = parsed.scheme == "wss"
    return parsed.hostname, port, path, use_tls


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def _get_str(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value if value else default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_optional(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _load_config() -> Config:
    tools_dir = Path(__file__).resolve().parents[3]
    _load_env_file(tools_dir / ".env")

    tick_seconds = _get_float("TICK_SECONDS", 1.0)
    min_duration = _get_int("TRACK_DURATION_MIN_SECONDS", 120)
    max_duration = _get_int("TRACK_DURATION_MAX_SECONDS", 360)
    if max_duration < min_duration:
        min_duration, max_duration = max_duration, min_duration

    return Config(
        mqtt_ws_url=_get_str("MQTT_WS_URL", "ws://ha-mosquitto-ws.don:80"),
        mqtt_username=_get_optional("MQTT_USERNAME"),
        mqtt_password=_get_optional("MQTT_PASSWORD"),
        mqtt_client_name=_get_str("MQTT_CLIENT_NAME", "mock-player"),
        mqtt_discovery_prefix=_get_str("MQTT_DISCOVERY_PREFIX", "homeassistant"),
        mqtt_state_prefix=_get_str("MQTT_STATE_PREFIX", "hmd"),
        device_name=_get_str("DEVICE_NAME", "Mock Player"),
        device_id=_get_str("DEVICE_ID", "mock-player"),
        entity_name=_get_str("ENTITY_NAME", "Mock Player"),
        entity_object_id=_get_str("ENTITY_OBJECT_ID", "mock_player"),
        tick_seconds=max(tick_seconds, 0.1),
        track_duration_min_seconds=min_duration,
        track_duration_max_seconds=max_duration,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    config = _load_config()
    LOGGER.info("Starting mock player with entity '%s'", config.entity_name)

    player = MockPlayer(config)
    shutdown_event = threading.Event()

    def _handle_signal(signum, frame):
        LOGGER.info("Shutting down mock player")
        player.stop()
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle_signal)

    while not shutdown_event.wait(1):
        continue


if __name__ == "__main__":
    main()
