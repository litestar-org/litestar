from __future__ import annotations

import dataclasses
from bdb import Breakpoint
from typing import TYPE_CHECKING, Any

import msgspec
from msgspec import Struct
from msgspec.inspect import IntType
from msgspec.structs import fields
import msgspec

from litestar.params import ParameterKwarg
from litestar.plugins import OpenAPISchemaPlugin
from litestar.types.empty import Empty
from litestar.typing import FieldDefinition
from litestar.utils.predicates import is_optional_union
from litestar.openapi.spec import Schema, Example

if TYPE_CHECKING:
    from msgspec.structs import FieldInfo

    from litestar._openapi.schema_generation import SchemaCreator


class StructSchemaPlugin(OpenAPISchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return not field_definition.is_union and field_definition.is_subclass_of(Struct)

    @classmethod
    def _get_field_extras(cls, field: msgspec.inspect.Field) -> tuple[ParameterKwarg | None, dict[str, Any]]:
        extra = {}
        kwargs = {}
        if isinstance(field.type, msgspec.inspect.Metadata):
            meta = field.type
            if extra_json_schema := meta.extra_json_schema:
                kwargs["title"] = extra_json_schema.get("title")
                kwargs["description"] = extra_json_schema.get("description")
                if examples := extra_json_schema.get("examples"):
                    kwargs["examples"] = [Example(value=e) for e in examples]
                kwargs["schema_extra"] = extra_json_schema.get("extra")
            extra = meta.extra
        else:
            meta = field
        field_type = meta.type
        if isinstance(
            field_type,
            (
                msgspec.inspect.IntType,
                msgspec.inspect.FloatType,
            ),
        ):
            kwargs["gt"] = field_type.gt
            kwargs["ge"] = field_type.ge
            kwargs["lt"] = field_type.lt
            kwargs["le"] = field_type.le
            kwargs["multiple_of"] = field_type.multiple_of
        elif isinstance(
            field_type,
            (
                msgspec.inspect.StrType,
                msgspec.inspect.BytesType,
                msgspec.inspect.ByteArrayType,
                msgspec.inspect.MemoryViewType,
            ),
        ):
            kwargs["min_length"] = field_type.min_length
            kwargs["max_length"] = field_type.max_length
            kwargs["pattern"] = field_type.pattern
        elif isinstance(field_type, msgspec.inspect.StrType):
            kwargs["pattern"] = field_type.pattern

        parameter_defaults = {
            f.name: default
            for f in dataclasses.fields(ParameterKwarg)
            if (default := f.default) is not dataclasses.MISSING
        }
        kwargs_without_defaults = {k: v for k, v in kwargs.items() if v != parameter_defaults[k]}

        if kwargs_without_defaults:
            return ParameterKwarg(**kwargs_without_defaults), extra
        return None, extra

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
            if kwarg_definition := cls._get_field_extras(field)[0]:
                field_definition_kwargs["kwarg_definition"] = kwarg_definition

            property_fields[field.encode_name] = FieldDefinition.from_annotation(
                annotation=type_hints[field.name],
                name=field.encode_name,
                default=field.default if field.default not in {msgspec.NODEFAULT, msgspec.UNSET} else Empty,
                **field_definition_kwargs
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
            # property_fields={
            #     field.encode_name: FieldDefinition.from_annotation(
            #         annotation=type_hints[field.name],
            #         name=field.encode_name,
            #         default=field.default if field.default not in {msgspec.NODEFAULT, msgspec.UNSET} else Empty,
            #         kwarg_definition=cls._get_field_extras(field)[0],
            #     )
            #     for field in struct_fields
            # },
        )
