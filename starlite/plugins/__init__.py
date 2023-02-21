from typing import Union

from .base import (
    InitPluginProtocol,
    OpenAPISchemaPluginProtocol,
    PluginMapping,
    SerializationPluginProtocol,
)

PluginProtocol = Union[SerializationPluginProtocol, InitPluginProtocol, OpenAPISchemaPluginProtocol]

__all__ = (
    "InitPluginProtocol",
    "OpenAPISchemaPluginProtocol",
    "PluginMapping",
    "PluginProtocol",
    "SerializationPluginProtocol",
)
