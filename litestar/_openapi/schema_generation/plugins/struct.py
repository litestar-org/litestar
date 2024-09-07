from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec
from msgspec import Struct

from litestar.openapi.spec import Schema
from litestar.plugins import OpenAPISchemaPlugin
from litestar.types.empty import Empty
from litestar.typing import FieldDefinition
from litestar.utils.predicates import is_optional_union
from litestar.plugins.core._msgspec import kwarg_definition_from_field

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator


class StructSchemaPlugin(OpenAPISchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return not field_definition.is_union and field_definition.is_subclass_of(Struct)

    @classmethod
    def to_openapi_schema(cls, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        def is_field_required(field: msgspec.inspect.Field) -> bool:
            return field.required or field.default_factory is Empty

        type_hints = field_definition.get_type_hints(include_extras=True, resolve_generics=True)
        struct_info: msgspec.inspect.StructType = msgspec.inspect.type_info(field_definition.type_)  # type: ignore[assignment]
        struct_fields = struct_info.fields

        property_fields = {}
        for field in struct_fields:
            field_definition_kwargs = {}
            if kwarg_definition := kwarg_definition_from_field(field)[0]:
                field_definition_kwargs["kwarg_definition"] = kwarg_definition

            property_fields[field.encode_name] = FieldDefinition.from_annotation(
                annotation=type_hints[field.name],
                name=field.encode_name,
                default=field.default if field.default not in {msgspec.NODEFAULT, msgspec.UNSET} else Empty,
                **field_definition_kwargs,
            )

        return schema_creator.create_component_schema(
            field_definition,
            required=sorted(
                [
                    field.encode_name
                    for field in struct_fields
                    if is_field_required(field=field) and not is_optional_union(type_hints[field.name])
                ]
            ),
            property_fields=property_fields,
        )
