from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.exceptions import MissingDependencyException
from litestar.openapi.spec import OpenAPIFormat, OpenAPIType, Schema
from litestar.plugins import OpenAPISchemaPlugin
from litestar.plugins.pydantic.utils import (
    get_model_info,
    is_pydantic_constrained_field,
    is_pydantic_model_class,
    is_pydantic_undefined,
    is_pydantic_v2,
)
from litestar.utils import is_class_and_subclass

try:
    import pydantic as _  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("pydantic") from e

try:
    import pydantic as pydantic_v2

    if not is_pydantic_v2(pydantic_v2):
        raise ImportError

    from pydantic import v1 as pydantic_v1
except ImportError:
    import pydantic as pydantic_v1  # type: ignore[no-redef]

    pydantic_v2 = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from litestar._openapi.schema_generation.schema import SchemaCreator
    from litestar.typing import FieldDefinition

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
    from pydantic import networks

    PYDANTIC_TYPE_MAP.update(
        {
            pydantic_v2.SecretStr: Schema(type=OpenAPIType.STRING),
            pydantic_v2.SecretBytes: Schema(type=OpenAPIType.STRING),
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
            pydantic_v2.AnyUrl: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URL),
            pydantic_v2.PastDate: Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.DATE,
                description="date with the constraint that the value must be in the past",
            ),
            pydantic_v2.FutureDate: Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.DATE,
                description="date with the constraint that the value must be in the future",
            ),
            pydantic_v2.PastDatetime: Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.DATE_TIME,
                description="datetime with the constraint that the value must be in the past",
            ),
            pydantic_v2.FutureDatetime: Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.DATE_TIME,
                description="datetime with the constraint that the value must be in the future",
            ),
            pydantic_v2.AwareDatetime: Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.DATE_TIME,
                description="datetime with the constraint that the value must have timezone info",
            ),
            pydantic_v2.NaiveDatetime: Schema(
                type=OpenAPIType.STRING,
                format=OpenAPIFormat.DATE_TIME,
                description="datetime with the constraint that the value must lack timezone info",
            ),
        }
    )
    if int(pydantic_v2.version.version_short().split(".")[1]) >= 10:
        # These were 'Annotated' type aliases before Pydantic 2.10, where they were
        # changed to proper classes. Using subscripted generics type in an 'isinstance'
        # check would raise a 'TypeError' on Python <3.12
        PYDANTIC_TYPE_MAP.update(
            {
                networks.HttpUrl: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URL),
                networks.AnyHttpUrl: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URL),
            }
        )


_supported_types = (pydantic_v1.BaseModel, *PYDANTIC_TYPE_MAP.keys())
if pydantic_v2 is not None:  # pragma: no cover
    _supported_types = (pydantic_v2.BaseModel, *_supported_types)


class PydanticSchemaPlugin(OpenAPISchemaPlugin):
    __slots__ = ("prefer_alias",)

    def __init__(self, prefer_alias: bool = False) -> None:
        self.prefer_alias = prefer_alias

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        return isinstance(value, _supported_types) or is_class_and_subclass(value, _supported_types)  # type: ignore[arg-type]

    @staticmethod
    def is_undefined_sentinel(value: Any) -> bool:
        return is_pydantic_undefined(value)

    @staticmethod
    def is_constrained_field(field_definition: FieldDefinition) -> bool:
        return is_pydantic_constrained_field(field_definition.annotation)

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
            return self.for_pydantic_model(field_definition=field_definition, schema_creator=schema_creator)
        return PYDANTIC_TYPE_MAP[field_definition.annotation]  # pragma: no cover

    @classmethod
    def for_pydantic_model(cls, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:  # pyright: ignore
        """Create a schema object for a given pydantic model class.

        Args:
            field_definition: FieldDefinition instance.
            schema_creator: An instance of the schema creator class

        Returns:
            A schema instance.
        """

        model_info = get_model_info(field_definition.annotation, prefer_alias=schema_creator.prefer_alias)

        return schema_creator.create_component_schema(
            field_definition,
            required=sorted(f.name for f in model_info.field_definitions.values() if f.is_required),
            property_fields=model_info.field_definitions,
            title=model_info.title,
            examples=None if model_info.example is None else [model_info.example],
        )
