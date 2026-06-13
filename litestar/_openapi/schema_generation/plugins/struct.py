from __future__ import annotations

import typing
from typing import TYPE_CHECKING, Literal, get_args, get_origin

import msgspec
from msgspec import Struct

from litestar.plugins import OpenAPISchemaPlugin
from litestar.plugins.core._msgspec import kwarg_definition_from_field
from litestar.params import ParameterKwarg
from litestar.types.empty import Empty
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.openapi.spec import Schema


class StructSchemaPlugin(OpenAPISchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return not field_definition.is_union and field_definition.is_subclass_of(Struct)

    @staticmethod
    def _is_field_required(field: msgspec.inspect.Field) -> bool:
        return field.required or field.default_factory is Empty

    @staticmethod
    def _extract_tag_field_kwarg_definition(
        struct_type: type[Struct], tag_field: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """Extract kwarg definition and extra metadata from a ClassVar tag field annotation.

        When a msgspec Struct uses ``ClassVar[Annotated[Literal[...], msgspec.Meta(...)]]``
        for the tag field, the metadata (description, title, examples, etc.) is not
        available via ``msgspec.inspect`` because ``ClassVar`` fields are excluded
        from the struct's field list. This method extracts that metadata so it can
        be included in the OpenAPI schema.

        Returns:
            A tuple of ``(kwarg_definition_kwargs, extra)`` where ``kwarg_definition_kwargs``
            is a dict suitable for constructing a ``ParameterKwarg`` (or ``None`` if no
            metadata was found), and ``extra`` is a dict of additional metadata.
        """
        type_hints = typing.get_type_hints(struct_type, include_extras=True)
        annotation = type_hints.get(tag_field)
        if annotation is None:
            return None, {}

        # Unwrap ClassVar to get the inner type
        if get_origin(annotation) is not typing.ClassVar:
            return None, {}

        inner = get_args(annotation)[0]
        origin = get_origin(inner)

        # Look for msgspec.Meta in Annotated metadata
        if origin is typing.Annotated:
            annotated_args = get_args(inner)
            # First arg is the actual type (e.g. Literal['1']), rest are metadata
            for meta in annotated_args[1:]:
                if isinstance(meta, msgspec.Meta):
                    kwargs: dict[str, Any] = {}
                    extra: dict[str, Any] = {}
                    if meta.description:
                        kwargs["description"] = meta.description
                    if meta.title:
                        kwargs["title"] = meta.title
                    if meta.examples:
                        from litestar.openapi.spec import Example

                        kwargs["examples"] = [Example(value=e) for e in meta.examples]
                    if meta.extra_json_schema:
                        if meta.extra_json_schema.get("description"):
                            kwargs.setdefault("description", meta.extra_json_schema["description"])
                        if meta.extra_json_schema.get("title"):
                            kwargs.setdefault("title", meta.extra_json_schema["title"])
                        if meta.extra_json_schema.get("examples"):
                            from litestar.openapi.spec import Example

                            kwargs.setdefault(
                                "examples",
                                [Example(value=e) for e in meta.extra_json_schema["examples"]],
                            )
                        if meta.extra_json_schema.get("extra"):
                            kwargs["schema_extra"] = meta.extra_json_schema["extra"]
                    if meta.extra:
                        extra = meta.extra
                    if kwargs:
                        return kwargs, extra
                    return None, extra

        return None, {}

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
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

        required = [field.encode_name for field in struct_fields if self._is_field_required(field=field)]

        # Support tagged unions: https://msgspec.dev/structs#tagged-unions
        # These structs contain a tag_field and a tag. Since these fields are added
        # dynamically, they are not present within the regular struct fields and don't
        # have any type annotation associated with them, so we create a FieldDefinition
        # manually
        if struct_info.tag_field:
            # using a Literal here will set these as a const in the schema
            tag_kwarg_definition_kwargs: dict[str, Any] | None = None
            tag_extra: dict[str, Any] = {}

            # Check if the tag field has a ClassVar annotation with msgspec.Meta metadata
            tag_kwarg_definition_kwargs, tag_extra = self._extract_tag_field_kwarg_definition(
                struct_type=field_definition.type_,  # type: ignore[arg-type]
                tag_field=struct_info.tag_field,
            )

            tag_field_definition_kwargs: dict[str, Any] = {}
            if tag_kwarg_definition_kwargs:
                tag_field_definition_kwargs["kwarg_definition"] = ParameterKwarg(**tag_kwarg_definition_kwargs)
            if tag_extra:
                tag_field_definition_kwargs["extra"] = tag_extra

            property_fields[struct_info.tag_field] = FieldDefinition.from_annotation(
                Literal[struct_info.tag],
                name=struct_info.tag_field,
                **tag_field_definition_kwargs,
            )
            required.append(struct_info.tag_field)

        return schema_creator.create_component_schema(
            field_definition,
            required=sorted(required),
            property_fields=property_fields,
        )
