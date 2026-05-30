# import logging
# from typing import TYPE_CHECKING, Any, cast

# import voluptuous as vol
# from homeassistant.components.mqtt import DATA_MQTT
# from homeassistant.components.mqtt.const import (
#     ATTR_DISCOVERY_HASH,
#     CONF_IDENTIFIERS,
#     CONF_SCHEMA,
# )
# from homeassistant.components.mqtt.discovery import (
#     MQTT_DISCOVERY_DONE,
#     MQTT_DISCOVERY_NEW,
#     MQTTDiscoveryPayload,
#     clear_discovery_hash,
# )
# from homeassistant.components.mqtt.entity import (
#     MqttEntity,
#     _verify_mqtt_config_entry_enabled_for_discovery,
#     async_handle_schema_error,
# )
# from homeassistant.components.mqtt.models import MqttSubentryData
# from homeassistant.components.mqtt.util import learn_more_url
# from homeassistant.config_entries import ConfigEntry
# from homeassistant.const import (
#     CONF_DEVICE,
#     CONF_ENTITY_CATEGORY,
#     CONF_NAME,
#     CONF_UNIQUE_ID,
# )
# from homeassistant.core import DOMAIN, HomeAssistant, callback
# from homeassistant.helpers.dispatcher import (
#     async_dispatcher_connect,
#     async_dispatcher_send,
# )
# from homeassistant.helpers.entity import Entity
# from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
# from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
# from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, VolSchemaType
# from homeassistant.util.yaml import dump as yaml_dump

# # Create a dedicated logger for debugging this module
# _LOGGER = logging.getLogger(__name__)
# _LOGGER.setLevel(logging.DEBUG)


# def _handle_discovery_failure(
#     hass: HomeAssistant,
#     discovery_payload: MQTTDiscoveryPayload,
# ) -> None:
#     """Handle discovery failure."""
#     discovery_hash = discovery_payload.discovery_data[ATTR_DISCOVERY_HASH]
#     _LOGGER.debug(
#         "MQTT Media Player: Handling discovery failure for hash: %s, payload: %s",
#         discovery_hash,
#         discovery_payload,
#     )
#     clear_discovery_hash(hass, discovery_hash)
#     async_dispatcher_send(hass, MQTT_DISCOVERY_DONE.format(*discovery_hash), None)
#     _LOGGER.debug(
#         "MQTT Media Player: Discovery failure handled, hash cleared and done signal sent"
#     )


# @callback
# def async_setup_entity_entry_helper(
#     hass: HomeAssistant,
#     entry: ConfigEntry,
#     entity_class: type[MqttEntity] | None,
#     domain: str,
#     async_add_entities: AddConfigEntryEntitiesCallback,
#     discovery_schema: VolSchemaType,
#     platform_schema_modern: VolSchemaType,
#     schema_class_mapping: dict[str, type[MqttEntity]] | None = None,
# ) -> None:
#     """Set up entity creation dynamically through MQTT discovery."""
#     _LOGGER.debug(
#         "MQTT Media Player: Starting async_setup_entity_entry_helper for domain: %s, "
#         "entry_id: %s, entity_class: %s, schema_class_mapping: %s",
#         domain,
#         entry.entry_id,
#         entity_class,
#         schema_class_mapping,
#     )
#     mqtt_data = hass.data[DATA_MQTT]

#     _LOGGER.debug("MQTT Media Player: Retrieved MQTT data")

#     @callback
#     def _async_migrate_subentry(
#         config: dict[str, Any], raw_config: dict[str, Any], migration_type: str
#     ) -> bool:
#         """Start a repair flow to allow migration of MQTT device subentries.

#         If a YAML config or discovery is detected using the ID
#         of an existing mqtt subentry, and exported configuration is detected,
#         and a repair flow is offered to migrate the subentry.
#         """
#         _LOGGER.debug(
#             "MQTT Media Player: Checking for subentry migration - migration_type: %s, "
#             "config: %s, raw_config: %s",
#             migration_type,
#             config,
#             raw_config,
#         )

#         if (
#             CONF_DEVICE in config
#             and CONF_IDENTIFIERS in config[CONF_DEVICE]
#             and config[CONF_DEVICE][CONF_IDENTIFIERS]
#             and (subentry_id := config[CONF_DEVICE][CONF_IDENTIFIERS][0])
#             in entry.subentries
#         ):
#             _LOGGER.debug(
#                 "MQTT Media Player: Found matching subentry for migration - subentry_id: %s, "
#                 "entry.subentries keys: %s",
#                 subentry_id,
#                 list(entry.subentries.keys()),
#             )
#             name: str = config[CONF_DEVICE].get(CONF_NAME, "-")
#             if migration_type == "subentry_migration_yaml":
#                 _LOGGER.info(
#                     "Starting migration repair flow for MQTT subentry %s "
#                     "for migration to YAML config: %s",
#                     subentry_id,
#                     raw_config,
#                 )
#                 _LOGGER.debug(
#                     "MQTT Media Player: Starting YAML migration repair flow for subentry: %s",
#                     subentry_id,
#                 )
#             elif migration_type == "subentry_migration_discovery":
#                 _LOGGER.info(
#                     "Starting migration repair flow for MQTT subentry %s "
#                     "for migration to configuration via MQTT discovery: %s",
#                     subentry_id,
#                     raw_config,
#                 )
#                 _LOGGER.debug(
#                     "MQTT Media Player: Starting discovery migration repair flow for subentry: %s",
#                     subentry_id,
#                 )
#             async_create_issue(
#                 hass,
#                 DOMAIN,
#                 subentry_id,
#                 issue_domain=DOMAIN,
#                 is_fixable=True,
#                 severity=IssueSeverity.WARNING,
#                 learn_more_url=learn_more_url(domain),
#                 data={
#                     "entry_id": entry.entry_id,
#                     "subentry_id": subentry_id,
#                     "name": name,
#                 },
#                 translation_placeholders={"name": name},
#                 translation_key=migration_type,
#             )
#             _LOGGER.debug(
#                 "MQTT Media Player: Created repair issue for subentry migration: %s",
#                 subentry_id,
#             )
#             return True

#         _LOGGER.debug(
#             "MQTT Media Player: No subentry migration needed - device config: %s",
#             config.get(CONF_DEVICE, "No device config found"),
#         )
#         return False

#     @callback
#     def _async_setup_entity_entry_from_discovery(
#         discovery_payload: MQTTDiscoveryPayload,
#     ) -> None:
#         """Set up an MQTT entity from discovery."""
#         nonlocal entity_class
#         _LOGGER.debug(
#             "MQTT Media Player: Starting discovery setup for payload: %s",
#             discovery_payload,
#         )

#         if not _verify_mqtt_config_entry_enabled_for_discovery(
#             hass, domain, discovery_payload
#         ):
#             _LOGGER.debug(
#                 "MQTT Media Player: Discovery verification failed for payload: %s",
#                 discovery_payload,
#             )
#             return

#         try:
#             _LOGGER.debug(
#                 "MQTT Media Player: Attempting to parse discovery schema for payload: %s",
#                 discovery_payload,
#             )
#             config: DiscoveryInfoType = discovery_schema(discovery_payload)
#             _LOGGER.debug(
#                 "MQTT Media Player: Discovery schema parsed successfully - config: %s",
#                 config,
#             )

#             if schema_class_mapping is not None:
#                 selected_class = schema_class_mapping[config[CONF_SCHEMA]]
#                 entity_class = selected_class
#                 _LOGGER.debug(
#                     "MQTT Media Player: Selected entity class from schema mapping - "
#                     "schema: %s, class: %s",
#                     config[CONF_SCHEMA],
#                     entity_class,
#                 )

#             if TYPE_CHECKING:
#                 assert entity_class is not None

#             if _async_migrate_subentry(
#                 config, discovery_payload, "subentry_migration_discovery"
#             ):
#                 _handle_discovery_failure(hass, discovery_payload)
#                 _LOGGER.debug(
#                     "MQTT discovery skipped, as device exists in subentry, "
#                     "and repair flow must be completed first"
#                 )
#                 _LOGGER.debug(
#                     "MQTT Media Player: Discovery skipped due to existing subentry - "
#                     "config: %s",
#                     config,
#                 )
#             else:
#                 _LOGGER.debug(
#                     "MQTT Media Player: Creating entity instance - class: %s, "
#                     "config: %s, discovery_data: %s",
#                     entity_class,
#                     config,
#                     discovery_payload.discovery_data,
#                 )
#                 entity_instance = entity_class(
#                     hass, config, entry, discovery_payload.discovery_data
#                 )
#                 _LOGGER.debug(
#                     "MQTT Media Player: Entity instance created successfully: %s",
#                     entity_instance,
#                 )
#                 async_add_entities([entity_instance])
#                 _LOGGER.debug(
#                     "MQTT Media Player: Entity added to Home Assistant successfully"
#                 )
#         except vol.Invalid as err:
#             _LOGGER.error(
#                 "MQTT Media Player: Schema validation error during discovery - "
#                 "error: %s, payload: %s",
#                 err,
#                 discovery_payload,
#             )
#             _handle_discovery_failure(hass, discovery_payload)
#             async_handle_schema_error(discovery_payload, err)
#         except Exception as exc:
#             _LOGGER.exception(
#                 "MQTT Media Player: Unexpected error during discovery setup - "
#                 "error: %s, payload: %s",
#                 exc,
#                 discovery_payload,
#             )
#             _handle_discovery_failure(hass, discovery_payload)
#             raise

#     _LOGGER.debug(
#         "MQTT Media Player: Registering discovery dispatcher for domain: %s",
#         domain,
#     )
#     dispatcher = async_dispatcher_connect(
#         hass,
#         MQTT_DISCOVERY_NEW.format(domain, "mqtt"),
#         _async_setup_entity_entry_from_discovery,
#     )
#     mqtt_data.reload_dispatchers.append(dispatcher)
#     _LOGGER.debug(
#         "MQTT Media Player: Discovery dispatcher registered successfully - signal: %s",
#         MQTT_DISCOVERY_NEW.format(domain, "mqtt"),
#     )

#     @callback
#     def _async_setup_entities() -> None:
#         """Set up MQTT items from subentries and configuration.yaml."""
#         nonlocal entity_class
#         _LOGGER.debug(
#             "MQTT Media Player: Starting entity setup for domain: %s, entry_id: %s",
#             domain,
#             entry.entry_id,
#         )

#         mqtt_data = hass.data[DATA_MQTT]
#         _LOGGER.debug(
#             "MQTT Media Player: Retrieved MQTT data - reload_handlers: %s, reload_schema: %s",
#             list(mqtt_data.reload_handlers.keys()),
#             list(mqtt_data.reload_schema.keys()),
#         )

#         config_yaml = mqtt_data.config

#         yaml_configs: list[ConfigType] = [
#             config
#             for config_item in config_yaml
#             for config_domain, configs in config_item.items()
#             for config in configs
#             if config_domain == domain
#         ]
#         _LOGGER.debug(
#             "MQTT Media Player: Found %d YAML configs for domain %s: %s",
#             len(yaml_configs),
#             domain,
#             yaml_configs,
#         )
#         # process subentry entity setup
#         _LOGGER.debug(
#             "MQTT Media Player: Processing %d subentries - subentry_ids: %s",
#             len(entry.subentries),
#             list(entry.subentries.keys()),
#         )
#         for config_subentry_id, subentry in entry.subentries.items():
#             _LOGGER.debug(
#                 "MQTT Media Player: Processing subentry - id: %s, title: %s, data keys: %s",
#                 config_subentry_id,
#                 subentry.title,
#                 list(subentry.data.keys()) if subentry.data else "No data",
#             )
#             subentry_data = cast(MqttSubentryData, subentry.data)
#             availability_config = subentry_data.get("availability", {})
#             subentry_entities: list[Entity] = []
#             device_config = subentry_data["device"].copy()  # type: ignore
#             device_mqtt_options = device_config.pop("mqtt_settings", {})
#             device_config["identifiers"] = config_subentry_id

#             _LOGGER.debug(
#                 "MQTT Media Player: Subentry device config - id: %s, device_config: %s, "
#                 "availability_config: %s, mqtt_options: %s",
#                 config_subentry_id,
#                 device_config,
#                 availability_config,
#                 device_mqtt_options,
#             )

#             components_count = len(subentry_data["components"].items())
#             _LOGGER.debug(
#                 "MQTT Media Player: Processing %d components for subentry %s",
#                 components_count,
#                 config_subentry_id,
#             )

#             for component_id, component_data in subentry_data["components"].items():  # type: ignore
#                 _LOGGER.debug(
#                     "MQTT Media Player: Processing component - subentry_id: %s, "
#                     "component_id: %s, platform: %s, domain: %s",
#                     config_subentry_id,
#                     component_id,
#                     component_data.get("platform", "Unknown"),
#                     domain,
#                 )
#                 if component_data["platform"] != domain:
#                     _LOGGER.debug(
#                         "MQTT Media Player: Skipping component %s - platform mismatch: %s != %s",
#                         component_id,
#                         component_data["platform"],
#                         domain,
#                     )
#                     continue

#                 component_config: dict[str, Any] = component_data.copy()
#                 component_config[CONF_UNIQUE_ID] = (
#                     f"{config_subentry_id}_{component_id}"
#                 )
#                 component_config[CONF_DEVICE] = device_config
#                 component_config.pop("platform")
#                 component_config.update(availability_config)
#                 component_config.update(device_mqtt_options)
#                 if (
#                     CONF_ENTITY_CATEGORY in component_config
#                     and component_config[CONF_ENTITY_CATEGORY] is None
#                 ):
#                     component_config.pop(CONF_ENTITY_CATEGORY)

#                 _LOGGER.debug(
#                     "MQTT Media Player: Final component config - subentry_id: %s, "
#                     "component_id: %s, config: %s",
#                     config_subentry_id,
#                     component_id,
#                     component_config,
#                 )

#                 try:
#                     _LOGGER.debug(
#                         "MQTT Media Player: Validating component config against schema - "
#                         "subentry_id: %s, component_id: %s",
#                         config_subentry_id,
#                         component_id,
#                     )
#                     config = platform_schema_modern(component_config)
#                     _LOGGER.debug(
#                         "MQTT Media Player: Schema validation successful - config: %s",
#                         config,
#                     )

#                     if schema_class_mapping is not None:
#                         selected_class = schema_class_mapping[config[CONF_SCHEMA]]
#                         entity_class = selected_class
#                         _LOGGER.debug(
#                             "MQTT Media Player: Selected entity class for subentry component - "
#                             "schema: %s, class: %s",
#                             config[CONF_SCHEMA],
#                             entity_class,
#                         )

#                     if TYPE_CHECKING:
#                         assert entity_class is not None

#                     _LOGGER.debug(
#                         "MQTT Media Player: Creating entity instance for subentry component - "
#                         "class: %s, unique_id: %s",
#                         entity_class,
#                         config.get(CONF_UNIQUE_ID),
#                     )
#                     entity_instance = entity_class(hass, config, entry, None)
#                     subentry_entities.append(entity_instance)
#                     _LOGGER.debug(
#                         "MQTT Media Player: Entity instance created for subentry component - "
#                         "instance: %s",
#                         entity_instance,
#                     )
#                 except vol.Invalid as exc:
#                     _LOGGER.error(
#                         "MQTT Media Player: Schema validation error for subentry component - "
#                         "subentry_id: %s, component_id: %s, error: %s, config: %s",
#                         config_subentry_id,
#                         component_id,
#                         exc,
#                         component_config,
#                     )
#                     _LOGGER.error(
#                         "Schema violation occurred when trying to set up "
#                         "entity from subentry %s %s %s: %s",
#                         config_subentry_id,
#                         subentry.title,
#                         subentry.data,
#                         exc,
#                     )

#             _LOGGER.debug(
#                 "MQTT Media Player: Adding %d entities for subentry %s: %s",
#                 len(subentry_entities),
#                 config_subentry_id,
#                 [str(entity) for entity in subentry_entities],
#             )
#             async_add_entities(subentry_entities, config_subentry_id=config_subentry_id)
#             _LOGGER.debug(
#                 "MQTT Media Player: Successfully added subentry entities for %s",
#                 config_subentry_id,
#             )

#         entities: list[Entity] = []
#         _LOGGER.debug(
#             "MQTT Media Player: Processing YAML configurations - count: %d",
#             len(yaml_configs),
#         )

#         for yaml_index, yaml_config in enumerate(yaml_configs):
#             _LOGGER.debug(
#                 "MQTT Media Player: Processing YAML config %d/%d - config: %s",
#                 yaml_index + 1,
#                 len(yaml_configs),
#                 yaml_config,
#             )
#             try:
#                 _LOGGER.debug(
#                     "MQTT Media Player: Validating YAML config against schema - index: %d",
#                     yaml_index,
#                 )
#                 config = platform_schema_modern(yaml_config)
#                 _LOGGER.debug(
#                     "MQTT Media Player: YAML schema validation successful - config: %s",
#                     config,
#                 )

#                 if schema_class_mapping is not None:
#                     selected_class = schema_class_mapping[config[CONF_SCHEMA]]
#                     entity_class = selected_class
#                     _LOGGER.debug(
#                         "MQTT Media Player: Selected entity class for YAML config - "
#                         "schema: %s, class: %s",
#                         config[CONF_SCHEMA],
#                         entity_class,
#                     )

#                 if TYPE_CHECKING:
#                     assert entity_class is not None

#                 if _async_migrate_subentry(
#                     config, yaml_config, "subentry_migration_yaml"
#                 ):
#                     _LOGGER.debug(
#                         "MQTT Media Player: Skipping YAML config due to subentry migration - "
#                         "index: %d",
#                         yaml_index,
#                     )
#                     continue

#                 _LOGGER.debug(
#                     "MQTT Media Player: Creating entity instance for YAML config - "
#                     "class: %s, unique_id: %s",
#                     entity_class,
#                     config.get(CONF_UNIQUE_ID),
#                 )
#                 entity_instance = entity_class(hass, config, entry, None)
#                 entities.append(entity_instance)
#                 _LOGGER.debug(
#                     "MQTT Media Player: Entity instance created for YAML config - "
#                     "instance: %s",
#                     entity_instance,
#                 )
#             except vol.Invalid as exc:
#                 error = str(exc)
#                 config_file = getattr(yaml_config, "__config_file__", "?")
#                 line = getattr(yaml_config, "__line__", "?")
#                 issue_id = hex(hash(frozenset(yaml_config)))
#                 yaml_config_str = yaml_dump(yaml_config)

#                 _LOGGER.error(
#                     "MQTT Media Player: Schema validation error for YAML config - "
#                     "index: %d, error: %s, config_file: %s, line: %s, config: %s",
#                     yaml_index,
#                     exc,
#                     config_file,
#                     line,
#                     yaml_config,
#                 )

#                 async_create_issue(
#                     hass,
#                     DOMAIN,
#                     issue_id,
#                     issue_domain=domain,
#                     is_fixable=False,
#                     severity=IssueSeverity.ERROR,
#                     learn_more_url=learn_more_url(domain),
#                     translation_placeholders={
#                         "domain": domain,
#                         "config_file": config_file,
#                         "line": line,
#                         "config": yaml_config_str,
#                         "error": error,
#                     },
#                     translation_key="invalid_platform_config",
#                 )
#                 _LOGGER.debug(
#                     "MQTT Media Player: Created issue for YAML config validation error - "
#                     "issue_id: %s",
#                     issue_id,
#                 )

#                 _LOGGER.error(
#                     "%s for manually configured MQTT %s item, in %s, line %s Got %s",
#                     error,
#                     domain,
#                     config_file,
#                     line,
#                     yaml_config,
#                 )

#         _LOGGER.debug(
#             "MQTT Media Player: Adding %d YAML entities: %s",
#             len(entities),
#             [str(entity) for entity in entities],
#         )
#         async_add_entities(entities)
#         _LOGGER.debug("MQTT Media Player: Successfully added YAML entities")

#     # When reloading we check manual configured items against the schema
#     # before reloading
#     _LOGGER.debug(
#         "MQTT Media Player: Registering reload schema and handlers for domain: %s",
#         domain,
#     )
#     mqtt_data.reload_schema[domain] = platform_schema_modern
#     # discover manual configured MQTT items
#     mqtt_data.reload_handlers[domain] = _async_setup_entities
#     _LOGGER.debug(
#         "MQTT Media Player: Reload handlers registered, calling initial setup"
#     )
#     _async_setup_entities()
#     _LOGGER.debug(
#         "MQTT Media Player: Entity setup helper completed for domain: %s",
#         domain,
#     )
