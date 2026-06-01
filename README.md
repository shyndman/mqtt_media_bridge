# MQTT Media Bridge

A Home Assistant custom component that creates MQTT-based media players with full playback control and media metadata support.

## Features

- **Full Media Control**: Play, pause, stop, next/previous track support
- **Volume Control**: Set volume level and mute/unmute
- **Seek Support**: Jump to specific positions in media
- **Rich Metadata**: Display track title, artist, album, duration, and album art
- **MQTT Discovery**: Automatic configuration through Home Assistant's MQTT discovery
- **HACS Compatible**: Easy installation through the Home Assistant Community Store

## Installation

### Via HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add `https://github.com/shyndman/mqtt_media_bridge` as a custom repository with category "Integration"
5. Click "Install" on the MQTT Media Bridge card
6. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/shyndman/mqtt_media_bridge/releases)
2. Extract the `mqtt_media_bridge` folder to your `custom_components` directory:
   ```
   <config_dir>/custom_components/mqtt_media_bridge/
   ```
3. Restart Home Assistant

## Configuration

This integration uses MQTT discovery. Your media player device should publish a discovery message to `homeassistant/media_player/<node_id>/<object_id>/config` with the appropriate configuration payload.

Once discovered, the media player will appear automatically in Home Assistant.

## MQTT Topics

The component supports the following MQTT topics for control and state:

### State Topics (Subscribe)

| Topic | Description | Example Value |
|-------|-------------|---------------|
| `state_topic` | Player state | `playing`, `paused`, `idle` |
| `media_title_topic` | Current track title | `"Bohemian Rhapsody"` |
| `media_artist_topic` | Current artist | `"Queen"` |
| `media_album_name_topic` | Album name | `"A Night at the Opera"` |
| `media_duration_topic` | Track duration (seconds) | `355` |
| `media_position_topic` | Current position (seconds) | `120` |
| `media_image_url_topic` | Album art URL | `"http://example.com/art.jpg"` |
| `volume_level_topic` | Volume level (0.0-1.0) | `0.75` |
| `volume_mute_state_topic` | Mute state | `true` or `false` |
| `shuffle_state_topic` | Shuffle state | `true` or `false` |
| `repeat_state_topic` | Repeat mode | `off`, `all`, or `one` |

### Command Topics (Publish)

| Topic | Description | Payload |
|-------|-------------|---------|
| `play_topic` | Start playback | Any payload |
| `pause_topic` | Pause playback | Any payload |
| `stop_topic` | Stop playback | Any payload |
| `next_track_topic` | Skip to next track | Any payload |
| `previous_track_topic` | Go to previous track | Any payload |
| `volume_set_topic` | Set volume level | `0.0` to `1.0` |
| `volume_mute_command_topic` | Toggle mute | `true` or `false` |
| `shuffle_set_topic` | Set shuffle mode | `true` or `false` |
| `repeat_set_topic` | Set repeat mode | `off`, `all`, or `one` |
| `seek_topic` | Seek to position | Position in seconds |

## Media Player Implementation

### Python Library

For implementing the media player side (the device that publishes state and responds to commands), check out [ha-mqtt-discoverable](https://github.com/shyndman/ha-mqtt-discoverable) - a Python library that makes it easy to create MQTT devices that work with this component.

```python
from ha_mqtt_discoverable import MediaPlayer

# Create a media player that publishes state to MQTT
player = MediaPlayer(
    mqtt_client=client,
    name="My Media Player",
    device_id="my_player_001"
)

# Update state
player.set_state("playing")
player.set_media_title("Bohemian Rhapsody")
player.set_media_artist("Queen")
```

### Manual MQTT Messages

You can also publish state manually from any MQTT client:

```bash
# Set player state to playing
mosquitto_pub -t "media/player/state" -m "playing"

# Update track metadata
mosquitto_pub -t "media/player/title" -m "Stairway to Heaven"
mosquitto_pub -t "media/player/artist" -m "Led Zeppelin"
mosquitto_pub -t "media/player/album" -m "Led Zeppelin IV"

# Update playback position
mosquitto_pub -t "media/player/position" -m "240"
mosquitto_pub -t "media/player/duration" -m "482"
```

### Controlling from Home Assistant

The media player will publish commands to the configured command topics when controlled through the Home Assistant UI:

```bash
# Monitor commands from Home Assistant
mosquitto_sub -t "media/player/cmd/+"
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/shyndman/mqtt_media_bridge.git
cd mqtt_media_bridge

# Run development setup
./scripts/setup

# Start development environment
./scripts/develop
```

### Running Tests

```bash
# Run linting
./scripts/lint
```

## Troubleshooting

### Media Player Not Appearing

1. Check that MQTT integration is properly configured in Home Assistant
2. Verify MQTT broker is running and accessible
3. Check Home Assistant logs for any error messages
4. Ensure all required topics are configured

### State Not Updating

1. Verify MQTT messages are being published to the correct topics
2. Use MQTT Explorer or mosquitto_sub to monitor topic activity
3. Check that topic names match exactly (case-sensitive)

### Album Art Not Showing

1. Ensure the URL is accessible from your Home Assistant instance
2. Set `media_image_remotely_accessible` to `true` if the image is hosted externally
3. Check that the image URL is properly formatted

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions:

1. Check the [troubleshooting section](#troubleshooting) above
2. Search [existing issues](https://github.com/shyndman/mqtt_media_bridge/issues)
3. Create a [new issue](https://github.com/shyndman/mqtt_media_bridge/issues/new) if needed

## Acknowledgments

- Home Assistant team for the excellent platform and MQTT integration
- The HACS community for making custom component distribution easy