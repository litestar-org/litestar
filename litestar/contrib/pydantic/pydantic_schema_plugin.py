from __future__ import annotations

from typing import Any

from typing_extensions import Annotated

from litestar._openapi.schema_generation.schema import SchemaCreator, _get_type_schema_name
from litestar.contrib.pydantic.utils import (
    is_pydantic_2_model,
    is_pydantic_model_class,
    pydantic_get_unwrapped_annotation_and_type_hints,
)
from litestar.exceptions import MissingDependencyException
from litestar.openapi.spec import Example, OpenAPIFormat, OpenAPIType, Schema
from litestar.plugins import OpenAPISchemaPluginProtocol
from litestar.types import Empty
from litestar.typing import FieldDefinition
from litestar.utils import is_class_and_subclass, is_undefined_sentinel

try:
    # check if we have pydantic v2 installed, and try to import both versions
    import pydantic as pydantic_v2
    from pydantic import v1 as pydantic_v1
except ImportError:
    # check if pydantic 1 is installed and import it
    try:
        import pydantic as pydantic_v1  # type: ignore[no-redef]

        pydantic_v2 = None  # type: ignore[assignment]
    except ImportError as e:
        raise MissingDependencyException("pydantic") from e


PYDANTIC_TYPE_MAP: dict[type[Any] | None | Any, Schema] = {
    pydantic_v1.ByteSize: Schema(type=OpenAPIType.INTEGER),
    pydantic_v1.EmailStr: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.EMAIL),
    pydantic_v1.IPvAnyAddress: Schema(
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
    pydantic_v1.IPvAnyInterface: Schema(
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
    pydantic_v1.IPvAnyNetwork: Schema(
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
    pydantic_v1.Json: Schema(type=OpenAPIType.OBJECT, format=OpenAPIFormat.JSON_POINTER),
    pydantic_v1.NameEmail: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.EMAIL, description="Name and email"),
    # removed in v2
    pydantic_v1.PyObject: Schema(
        type=OpenAPIType.STRING,
        description="dot separated path identifying a python object, e.g. 'decimal.Decimal'",
    ),
    # annotated in v2
    pydantic_v1.UUID1: Schema(
        type=OpenAPIType.STRING,
        format=OpenAPIFormat.UUID,
        description="UUID1 string",
    ),
    pydantic_v1.UUID3: Schema(
        type=OpenAPIType.STRING,
        format=OpenAPIFormat.UUID,
        description="UUID3 string",
    ),
    pydantic_v1.UUID4: Schema(
        type=OpenAPIType.STRING,
        format=OpenAPIFormat.UUID,
        description="UUID4 string",
    ),
    pydantic_v1.UUID5: Schema(
        type=OpenAPIType.STRING,
        format=OpenAPIFormat.UUID,
        description="UUID5 string",
    ),
    pydantic_v1.DirectoryPath: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI_REFERENCE),
    pydantic_v1.AnyUrl: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URL),
    pydantic_v1.AnyHttpUrl: Schema(
        type=OpenAPIType.STRING, format=OpenAPIFormat.URL, description="must be a valid HTTP based URL"
    ),
    pydantic_v1.FilePath: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI_REFERENCE),
    pydantic_v1.HttpUrl: Schema(
        type=OpenAPIType.STRING,
        format=OpenAPIFormat.URL,
        description="must be a valid HTTP based URL",
        max_length=2083,
    ),
    pydantic_v1.RedisDsn: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI, description="redis DSN"),
    pydantic_v1.PostgresDsn: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI, description="postgres DSN"),
    pydantic_v1.SecretBytes: Schema(type=OpenAPIType.STRING),
    pydantic_v1.SecretStr: Schema(type=OpenAPIType.STRING),
    pydantic_v1.StrictBool: Schema(type=OpenAPIType.BOOLEAN),
    pydantic_v1.StrictBytes: Schema(type=OpenAPIType.STRING),
    pydantic_v1.StrictFloat: Schema(type=OpenAPIType.NUMBER),
    pydantic_v1.StrictInt: Schema(type=OpenAPIType.INTEGER),
    pydantic_v1.StrictStr: Schema(type=OpenAPIType.STRING),
    pydantic_v1.NegativeFloat: Schema(type=OpenAPIType.NUMBER, exclusive_maximum=0.0),
    pydantic_v1.NegativeInt: Schema(type=OpenAPIType.INTEGER, exclusive_maximum=0),
    pydantic_v1.NonNegativeInt: Schema(type=OpenAPIType.INTEGER, minimum=0),
    pydantic_v1.NonPositiveFloat: Schema(type=OpenAPIType.NUMBER, maximum=0.0),
    pydantic_v1.PaymentCardNumber: Schema(type=OpenAPIType.STRING, min_length=12, max_length=19),
    pydantic_v1.PositiveFloat: Schema(type=OpenAPIType.NUMBER, exclusive_minimum=0.0),
    pydantic_v1.PositiveInt: Schema(type=OpenAPIType.INTEGER, exclusive_minimum=0),
}

if pydantic_v2 is not None:  # pragma: no cover
    PYDANTIC_TYPE_MAP.update(
        {
            pydantic_v2.ByteSize: Schema(type=OpenAPIType.INTEGER),
            pydantic_v2.EmailStr: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.EMAIL),
            pydantic_v2.IPvAnyAddress: Schema(
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
            pydantic_v2.IPvAnyInterface: Schema(
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
            pydantic_v2.IPvAnyNetwork: Schema(
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
            pydantic_v2.Json: Schema(type=OpenAPIType.OBJECT, format=OpenAPIFormat.JSON_POINTER),
            pydantic_v2.NameEmail: Schema(
                type=OpenAPIType.STRING, format=OpenAPIFormat.EMAIL, description="Name and email"
            ),
        }
    )


_supported_types = (pydantic_v1.BaseModel, *PYDANTIC_TYPE_MAP.keys())
if pydantic_v2 is not None:  # pragma: no cover
    _supported_types = (pydantic_v2.BaseModel, *_supported_types)


class PydanticSchemaPlugin(OpenAPISchemaPluginProtocol):
    __slots__ = ("prefer_alias",)

    def __init__(self, prefer_alias: bool = False) -> None:
        self.prefer_alias = prefer_alias

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        return isinstance(value, _supported_types) or is_class_and_subclass(value, _supported_types)  # type: ignore

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
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
            return self.for_pydantic_model(
                field_definition=field_definition, annotation=field_definition.annotation, schema_creator=schema_creator
            )
        return PYDANTIC_TYPE_MAP[field_definition.annotation]  # pragma: no cover

    @classmethod
    def for_pydantic_model(
        cls,
        field_definition: FieldDefinition,
        annotation: type[pydantic_v1.BaseModel | pydantic_v2.BaseModel],  # pyright: ignore
        schema_creator: SchemaCreator,
    ) -> Schema:  # pyright: ignore
        """Create a schema object for a given pydantic model class.

        Args:
            annotation: A pydantic model class.
            field_definition: FieldDefinition instance.
            schema_creator: An instance of the schema creator class

        Returns:
            A schema instance.
        """

        annotation = field_definition.annotation
        unwrapped_annotation, annotation_hints = pydantic_get_unwrapped_annotation_and_type_hints(annotation)

        if is_pydantic_2_model(annotation):
            model_config = annotation.model_config
            model_field_info = unwrapped_annotation.model_fields
            title = model_config.get("title")
            example = model_config.get("example")
            is_v2_model = True
        else:
            model_config = annotation.__config__  # type: ignore[union-attr, assignment]
            model_field_info = unwrapped_annotation.__fields__
            title = getattr(model_config, "title", None)
            example = getattr(model_config, "example", None)
            is_v2_model = False

        model_fields: dict[str, pydantic_v1.fields.FieldInfo | pydantic_v2.fields.FieldInfo] = {  # pyright: ignore
            k: getattr(f, "field_info", f) for k, f in model_field_info.items()
        }

        field_definitions = {
            f.alias
            if f.alias and schema_creator.prefer_alias
            else k: FieldDefinition.from_kwarg(
                annotation=Annotated[annotation_hints[k], f, f.metadata]  # type: ignore[union-attr]
                if is_v2_model
                else Annotated[annotation_hints[k], f],  # pyright: ignore
                name=f.alias if f.alias and schema_creator.prefer_alias else k,
                default=Empty if is_undefined_sentinel(f.default) else f.default,
            )
            for k, f in model_fields.items()
        }

        return Schema(
            required=sorted(f.name for f in field_definitions.values() if f.is_required),
            properties={k: schema_creator.for_field_definition(f) for k, f in field_definitions.items()},
            type=OpenAPIType.OBJECT,
            title=title or _get_type_schema_name(field_definition),
            examples=[Example(example)] if example else None,  # type: ignore[arg-type]
        )
