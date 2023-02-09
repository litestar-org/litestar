from typing import Union

from .base import (
    InitPluginProtocol,
    OpenAPISchemaPluginProtocol,
    PluginMapping,
    SerializationPluginProtocol,
    get_plugin_for_value,
)

PluginProtocol = Union[SerializationPluginProtocol, InitPluginProtocol, OpenAPISchemaPluginProtocol]

__all__ = (
    "InitPluginProtocol",
    "OpenAPISchemaPluginProtocol",
    "PluginMapping",
    "PluginProtocol",
    "SerializationPluginProtocol",
    "get_plugin_for_value",
)
