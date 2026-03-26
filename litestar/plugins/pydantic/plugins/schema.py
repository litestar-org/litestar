from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pydantic
from pydantic import networks

from litestar.openapi.spec import OpenAPIFormat, OpenAPIType, Reference, Schema
from litestar.plugins import OpenAPISchemaPlugin
from litestar.plugins.pydantic.utils import (
    get_model_info,
    is_pydantic_model_class,
    is_pydantic_root_model,
    is_pydantic_undefined,
)
from litestar.typing import FieldDefinition
from litestar.utils import is_class_and_subclass

if TYPE_CHECKING:
    from litestar._openapi.schema_generation.schema import SchemaCreator

PYDANTIC_TYPE_MAP: dict[type[Any] | None | Any, Schema] = {
    pydantic.SecretStr: Schema(type=OpenAPIType.STRING),
    pydantic.SecretBytes: Schema(type=OpenAPIType.STRING),
    pydantic.ByteSize: Schema(type=OpenAPIType.INTEGER),
    pydantic.EmailStr: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.EMAIL),
    pydantic.IPvAnyAddress: Schema(
        one_of=[
            Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.IPV4,
                description="IPv4 address",
            ),
            Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.IPV6,
                description="IPv6 address",
            ),
        ]
    ),
    pydantic.IPvAnyInterface: Schema(
        one_of=[
            Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.IPV4,
                description="IPv4 interface",
            ),
            Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.IPV6,
                description="IPv6 interface",
            ),
        ]
    ),
    pydantic.IPvAnyNetwork: Schema(
        one_of=[
            Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.IPV4,
                description="IPv4 network",
            ),
            Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.IPV6,
                description="IPv6 network",
            ),
        ]
    ),
    pydantic.Json: Schema(type=OpenAPIType.OBJECT, format=OpenAPIFormat.JSON_POINTER),
    pydantic.NameEmail: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.EMAIL, description="Name and email"),
    pydantic.AnyUrl: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URL),
    pydantic.PastDate: Schema(
        type=OpenAPIType.STRING,
        format=OpenAPIFormat.DATE,
        description="date with the constraint that the value must be in the past",
    ),
    pydantic.FutureDate: Schema(
        type=OpenAPIType.STRING,
        format=OpenAPIFormat.DATE,
        description="date with the constraint that the value must be in the future",
    ),
    pydantic.PastDatetime: Schema(
        type=OpenAPIType.STRING,
        format=OpenAPIFormat.DATE_TIME,
        description="datetime with the constraint that the value must be in the past",
    ),
    pydantic.FutureDatetime: Schema(
        type=OpenAPIType.STRING,
        format=OpenAPIFormat.DATE_TIME,
        description="datetime with the constraint that the value must be in the future",
    ),
    pydantic.AwareDatetime: Schema(
        type=OpenAPIType.STRING,
        format=OpenAPIFormat.DATE_TIME,
        description="datetime with the constraint that the value must have timezone info",
    ),
    pydantic.NaiveDatetime: Schema(
        type=OpenAPIType.STRING,
        format=OpenAPIFormat.DATE_TIME,
        description="datetime with the constraint that the value must lack timezone info",
    ),
}

if int(pydantic.version.version_short().split(".")[1]) >= 10:
    # These were 'Annotated' type aliases before Pydantic 2.10, where they were
    # changed to proper classes. Using subscripted generics type in an 'isinstance'
    # check would raise a 'TypeError' on Python <3.12
    PYDANTIC_TYPE_MAP.update(
        {
            networks.HttpUrl: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URL),
            networks.AnyHttpUrl: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URL),
        }
    )


_supported_types = (pydantic.BaseModel, *PYDANTIC_TYPE_MAP.keys())


class PydanticSchemaPlugin(OpenAPISchemaPlugin):
    def __init__(self, prefer_alias: bool = False) -> None:
        self.prefer_alias = prefer_alias

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        return isinstance(value, _supported_types) or is_class_and_subclass(value, _supported_types)  # type: ignore[arg-type]

    @staticmethod
    def is_undefined_sentinel(value: Any) -> bool:
        return is_pydantic_undefined(value)

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        """Given a type annotation, transform it into an OpenAPI schema class.

        Args:
            field_definition: FieldDefinition instance.
            schema_creator: An instance of the schema creator class

        Returns:
            An :class:`OpenAPI <litestar.openapi.spec.schema.Schema>` instance.
        """
        if schema_creator.prefer_alias != self.prefer_alias:
            schema_creator.prefer_alias = True
        if is_pydantic_model_class(field_definition.annotation):
            return self.for_pydantic_model(field_definition=field_definition, schema_creator=schema_creator)
        return PYDANTIC_TYPE_MAP[field_definition.annotation]  # pragma: no cover

    @classmethod
    def for_pydantic_model(cls, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:  # pyright: ignore
        """Create a schema object for a given pydantic model class.

        Args:
            field_definition: FieldDefinition instance.
            schema_creator: An instance of the schema creator class

        Returns:
            A schema instance.
        """

        model_info = get_model_info(field_definition.annotation, prefer_alias=schema_creator.prefer_alias)

        # Handle RootModel: generate schema for the root field content instead of treating it as a regular field
        if is_pydantic_root_model(field_definition.annotation) and (
            root_field := model_info.field_definitions.get("root")
        ):
            root_field_def = FieldDefinition.from_annotation(
                annotation=root_field.annotation,
                name=field_definition.name,
                default=field_definition.default,
                extra=field_definition.extra,
            )
            return schema_creator.for_field_definition(root_field_def)

        return schema_creator.create_component_schema(
            field_definition,
            required=sorted(f.name for f in model_info.field_definitions.values() if f.is_required),
            property_fields=model_info.field_definitions,
            title=model_info.title,
            examples=None if model_info.example is None else [model_info.example],
        )
