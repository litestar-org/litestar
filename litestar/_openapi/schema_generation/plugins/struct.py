from __future__ import annotations

from typing import TYPE_CHECKING

from msgspec import Struct
from msgspec.structs import fields

from litestar._openapi.schema_generation.schema import _get_type_schema_name
from litestar.openapi.spec import OpenAPIType, Schema
from litestar.plugins import OpenAPISchemaPlugin
from litestar.types.empty import Empty
from litestar.typing import FieldDefinition
from litestar.utils.predicates import is_optional_union

if TYPE_CHECKING:
    from msgspec.structs import FieldInfo

    from litestar._openapi.schema_generation import SchemaCreator


class StructSchemaPlugin(OpenAPISchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.is_subclass_of(Struct)

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        def _is_field_required(field: FieldInfo) -> bool:
            return field.required or field.default_factory is Empty

        unwrapped_annotation = field_definition.origin or field_definition.annotation
        type_hints = field_definition.get_type_hints(include_extras=True, resolve_generics=True)
        struct_fields = fields(unwrapped_annotation)

        return Schema(
            required=sorted(
                [
                    field.encode_name
                    for field in struct_fields
                    if _is_field_required(field=field) and not is_optional_union(type_hints[field.name])
                ]
            ),
            properties={
                field.encode_name: schema_creator.for_field_definition(
                    FieldDefinition.from_kwarg(type_hints[field.name], field.encode_name)
                )
                for field in struct_fields
            },
            type=OpenAPIType.OBJECT,
            title=_get_type_schema_name(field_definition),
        )
