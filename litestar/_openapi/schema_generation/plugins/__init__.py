from .dataclass import DataclassSchemaPlugin
from .struct import StructSchemaPlugin
from .typed_dict import TypedDictSchemaPlugin

__all__ = ("openapi_schema_plugins",)

openapi_schema_plugins = [
    StructSchemaPlugin(),
    DataclassSchemaPlugin(),
    TypedDictSchemaPlugin(),
]
