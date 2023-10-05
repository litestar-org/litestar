from __future__ import annotations

from typing import Any

from typing_extensions import Annotated, get_type_hints

from litestar._openapi.schema_generation.schema import SchemaCreator, _get_type_schema_name
from litestar.exceptions import MissingDependencyException
from litestar.openapi.spec import Example, OpenAPIFormat, OpenAPIType, Schema
from litestar.plugins import OpenAPISchemaPluginProtocol
from litestar.types import Empty
from litestar.typing import FieldDefinition
from litestar.utils import is_class_and_subclass, is_pydantic_model_class, is_undefined_sentinel

try:
    import pydantic
except ImportError as e:
    raise MissingDependencyException("pydantic") from e

PYDANTIC_TYPE_MAP: dict[type[Any] | None | Any, Schema] = {
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
}

if pydantic.VERSION.startswith("1"):  # pragma: no cover
    # pydantic v1 values only - some are removed in v2, others are Annotated[] based and require a different
    # logic
    PYDANTIC_TYPE_MAP.update(
        {
            # removed in v2
            pydantic.PyObject: Schema(
                type=OpenAPIType.STRING,
                description="dot separated path identifying a python object, e.g. 'decimal.Decimal'",
            ),
            # annotated in v2
            pydantic.UUID1: Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.UUID,
                description="UUID1 string",
            ),
            pydantic.UUID3: Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.UUID,
                description="UUID3 string",
            ),
            pydantic.UUID4: Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.UUID,
                description="UUID4 string",
            ),
            pydantic.UUID5: Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.UUID,
                description="UUID5 string",
            ),
            pydantic.DirectoryPath: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI_REFERENCE),
            pydantic.AnyUrl: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URL),
            pydantic.AnyHttpUrl: Schema(
                type=OpenAPIType.STRING, format=OpenAPIFormat.URL, description="must be a valid HTTP based URL"
            ),
            pydantic.FilePath: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI_REFERENCE),
            pydantic.HttpUrl: Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.URL,
                description="must be a valid HTTP based URL",
                max_length=2083,
            ),
            pydantic.RedisDsn: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI, description="redis DSN"),
            pydantic.PostgresDsn: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI, description="postgres DSN"),
            pydantic.SecretBytes: Schema(type=OpenAPIType.STRING),
            pydantic.SecretStr: Schema(type=OpenAPIType.STRING),
            pydantic.StrictBool: Schema(type=OpenAPIType.BOOLEAN),
            pydantic.StrictBytes: Schema(type=OpenAPIType.STRING),
            pydantic.StrictFloat: Schema(type=OpenAPIType.NUMBER),
            pydantic.StrictInt: Schema(type=OpenAPIType.INTEGER),
            pydantic.StrictStr: Schema(type=OpenAPIType.STRING),
            pydantic.NegativeFloat: Schema(type=OpenAPIType.NUMBER, exclusive_maximum=0.0),
            pydantic.NegativeInt: Schema(type=OpenAPIType.INTEGER, exclusive_maximum=0),
            pydantic.NonNegativeInt: Schema(type=OpenAPIType.INTEGER, minimum=0),
            pydantic.NonPositiveFloat: Schema(type=OpenAPIType.NUMBER, maximum=0.0),
            pydantic.PaymentCardNumber: Schema(type=OpenAPIType.STRING, min_length=12, max_length=19),
            pydantic.PositiveFloat: Schema(type=OpenAPIType.NUMBER, exclusive_minimum=0.0),
            pydantic.PositiveInt: Schema(type=OpenAPIType.INTEGER, exclusive_minimum=0),
        }
    )

_supported_types = (pydantic.BaseModel, *list(PYDANTIC_TYPE_MAP.keys()))


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
            return self.for_pydantic_model(annotation=field_definition.annotation, schema_creator=schema_creator)
        return PYDANTIC_TYPE_MAP[field_definition.annotation]  # pragma: no cover

    @classmethod
    def for_pydantic_model(
        cls, annotation: type[pydantic.BaseModel], schema_creator: SchemaCreator
    ) -> Schema:  # pyright: ignore
        """Create a schema object for a given pydantic model class.

        Args:
            annotation: A pydantic model class.
            schema_creator: An instance of the schema creator class

        Returns:
            A schema instance.
        """

        annotation_hints = get_type_hints(annotation, include_extras=True)
        model_config = getattr(annotation, "__config__", getattr(annotation, "model_config", Empty))
        model_fields: dict[str, pydantic.fields.FieldInfo] = {
            k: getattr(f, "field_info", f)
            for k, f in getattr(annotation, "__fields__", getattr(annotation, "model_fields", {})).items()
        }

        # pydantic v2 logic
        if isinstance(model_config, dict):
            title = model_config.get("title")
            example = model_config.get("example")
        else:  # pragma: no cover
            title = getattr(model_config, "title", None)
            example = getattr(model_config, "example", None)

        field_definitions = {
            f.alias
            if f.alias and schema_creator.prefer_alias
            else k: FieldDefinition.from_kwarg(
                annotation=Annotated[annotation_hints[k], f, f.metadata]  # pyright: ignore
                if pydantic.VERSION.startswith("2")
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
            title=title or _get_type_schema_name(annotation),
            examples=[Example(example)] if example else None,
        )
