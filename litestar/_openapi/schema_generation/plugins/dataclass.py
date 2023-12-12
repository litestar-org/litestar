from __future__ import annotations

from dataclasses import MISSING, fields
from typing import TYPE_CHECKING

from litestar._openapi.schema_generation.schema import _get_type_schema_name
from litestar.openapi.spec import OpenAPIType, Schema
from litestar.plugins import OpenAPISchemaPlugin
from litestar.typing import FieldDefinition
from litestar.utils.predicates import is_optional_union

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator


class DataclassSchemaPlugin(OpenAPISchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.is_dataclass_type

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        unwrapped_annotation = field_definition.origin or field_definition.annotation
        type_hints = field_definition.get_type_hints(include_extras=True, resolve_generics=True)
        return Schema(
            required=sorted(
                [
                    field.name
                    for field in fields(unwrapped_annotation)
                    if (
                        field.default is MISSING
                        and field.default_factory is MISSING
                        and not is_optional_union(type_hints[field.name])
                    )
                ]
            ),
            properties={
                k: schema_creator.for_field_definition(FieldDefinition.from_kwarg(v, k)) for k, v in type_hints.items()
            },
            type=OpenAPIType.OBJECT,
            title=_get_type_schema_name(field_definition),
        )
