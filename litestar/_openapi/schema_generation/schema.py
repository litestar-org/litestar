from __future__ import annotations

from collections import deque
from copy import copy
from dataclasses import MISSING, fields
from datetime import date, datetime, time, timedelta
from enum import EnumMeta
from inspect import getdoc
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    DefaultDict,
    Deque,
    Dict,
    FrozenSet,
    Hashable,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    MutableSequence,
    OrderedDict,
    Pattern,
    Sequence,
    Set,
    Tuple,
    cast,
)
from uuid import UUID

from _decimal import Decimal
from typing_extensions import get_args, get_type_hints

from litestar._openapi.schema_generation.constrained_fields import (
    create_constrained_field_schema,
)
from litestar._openapi.schema_generation.examples import create_examples_for_field
from litestar._openapi.schema_generation.utils import sort_schemas_and_references
from litestar._signature.field import SignatureField
from litestar.constants import UNDEFINED_SENTINELS
from litestar.datastructures import UploadFile
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec import Reference
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.openapi.spec.schema import Schema, SchemaDataContainer
from litestar.pagination import ClassicPagination, CursorPagination, OffsetPagination
from litestar.serialization import encode_json
from litestar.types import DataclassProtocol, Empty, TypedDictClass
from litestar.utils.predicates import (
    is_dataclass_class,
    is_pydantic_constrained_field,
    is_pydantic_model_class,
    is_typed_dict,
)
from litestar.utils.typing import get_origin_or_inner_type, make_non_optional_union

if TYPE_CHECKING:
    from litestar.plugins import OpenAPISchemaPluginProtocol

    try:
        from pydantic import (
            BaseModel,
            ConstrainedBytes,
            ConstrainedDate,
            ConstrainedDecimal,
            ConstrainedFloat,
            ConstrainedFrozenSet,
            ConstrainedInt,
            ConstrainedList,
            ConstrainedSet,
            ConstrainedStr,
        )
    except ImportError:
        BaseModel = Any  # type: ignore
        ConstrainedBytes = Any  # type: ignore
        ConstrainedDate = Any  # type: ignore
        ConstrainedDecimal = Any  # type: ignore
        ConstrainedFloat = Any  # type: ignore
        ConstrainedFrozenSet = Any  # type: ignore
        ConstrainedInt = Any  # type: ignore
        ConstrainedList = Any  # type: ignore
        ConstrainedSet = Any  # type: ignore
        ConstrainedStr = Any  # type: ignore

try:
    import pydantic

    PYDANTIC_TYPE_MAP: dict[type[Any] | None | Any, Schema] = {
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
        pydantic.AnyHttpUrl: Schema(
            type=OpenAPIType.STRING, format=OpenAPIFormat.URL, description="must be a valid HTTP based URL"
        ),
        pydantic.AnyUrl: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URL),
        pydantic.ByteSize: Schema(type=OpenAPIType.INTEGER),
        pydantic.DirectoryPath: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI_REFERENCE),
        pydantic.EmailStr: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.EMAIL),
        pydantic.FilePath: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI_REFERENCE),
        pydantic.HttpUrl: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.URL,
            description="must be a valid HTTP based URL",
            max_length=2083,
        ),
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
        pydantic.NegativeFloat: Schema(type=OpenAPIType.NUMBER, exclusive_maximum=0.0),
        pydantic.NegativeInt: Schema(type=OpenAPIType.INTEGER, exclusive_maximum=0),
        pydantic.NonNegativeInt: Schema(type=OpenAPIType.INTEGER, minimum=0),
        pydantic.NonPositiveFloat: Schema(type=OpenAPIType.NUMBER, maximum=0.0),
        pydantic.PaymentCardNumber: Schema(type=OpenAPIType.STRING, min_length=12, max_length=19),
        pydantic.PositiveFloat: Schema(type=OpenAPIType.NUMBER, exclusive_minimum=0.0),
        pydantic.PositiveInt: Schema(type=OpenAPIType.INTEGER, exclusive_minimum=0),
        pydantic.PostgresDsn: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI, description="postgres DSN"),
        pydantic.PyObject: Schema(
            type=OpenAPIType.STRING,
            description="dot separated path identifying a python object, e.g. 'decimal.Decimal'",
        ),
        pydantic.RedisDsn: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI, description="redis DSN"),
        pydantic.SecretBytes: Schema(type=OpenAPIType.STRING),
        pydantic.SecretStr: Schema(type=OpenAPIType.STRING),
        pydantic.StrictBool: Schema(type=OpenAPIType.BOOLEAN),
        pydantic.StrictBytes: Schema(type=OpenAPIType.STRING),
        pydantic.StrictFloat: Schema(type=OpenAPIType.NUMBER),
        pydantic.StrictInt: Schema(type=OpenAPIType.INTEGER),
        pydantic.StrictStr: Schema(type=OpenAPIType.STRING),
    }
except ImportError:
    PYDANTIC_TYPE_MAP = {}

__all__ = ("create_schema",)

KWARG_MODEL_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP: dict[str, str] = {
    "default": "default",
    "multiple_of": "multipleOf",
    "ge": "minimum",
    "le": "maximum",
    "lt": "exclusiveMaximum",
    "gt": "exclusiveMinimum",
    "max_length": "maxLength",
    "min_length": "minLength",
    "max_items": "maxItems",
    "min_items": "minItems",
    "regex": "pattern",
    "title": "title",
    "description": "description",
    "examples": "examples",
    "external_docs": "externalDocs",
    "content_encoding": "contentEncoding",
}

TYPE_MAP: dict[type[Any] | None | Any, Schema] = {
    Decimal: Schema(type=OpenAPIType.NUMBER),
    DefaultDict: Schema(type=OpenAPIType.OBJECT),
    Deque: Schema(type=OpenAPIType.ARRAY),
    Dict: Schema(type=OpenAPIType.OBJECT),
    FrozenSet: Schema(type=OpenAPIType.ARRAY),
    IPv4Address: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4),
    IPv4Interface: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4),
    IPv4Network: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4),
    IPv6Address: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6),
    IPv6Interface: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6),
    IPv6Network: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6),
    Iterable: Schema(type=OpenAPIType.ARRAY),
    List: Schema(type=OpenAPIType.ARRAY),
    Mapping: Schema(type=OpenAPIType.OBJECT),
    MutableMapping: Schema(type=OpenAPIType.OBJECT),
    MutableSequence: Schema(type=OpenAPIType.ARRAY),
    None: Schema(type=OpenAPIType.NULL),
    OrderedDict: Schema(type=OpenAPIType.OBJECT),
    Path: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI),
    Pattern: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.REGEX),
    Sequence: Schema(type=OpenAPIType.ARRAY),
    Set: Schema(type=OpenAPIType.ARRAY),
    Tuple: Schema(type=OpenAPIType.ARRAY),
    UUID: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.UUID, description="Any UUID string"),
    bool: Schema(type=OpenAPIType.BOOLEAN),
    bytearray: Schema(type=OpenAPIType.STRING),
    bytes: Schema(type=OpenAPIType.STRING),
    date: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DATE),
    datetime: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DATE_TIME),
    deque: Schema(type=OpenAPIType.ARRAY),
    dict: Schema(type=OpenAPIType.OBJECT),
    float: Schema(type=OpenAPIType.NUMBER),
    frozenset: Schema(type=OpenAPIType.ARRAY),
    int: Schema(type=OpenAPIType.INTEGER),
    list: Schema(type=OpenAPIType.ARRAY),
    set: Schema(type=OpenAPIType.ARRAY),
    str: Schema(type=OpenAPIType.STRING),
    time: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DURATION),
    timedelta: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DURATION),
    tuple: Schema(type=OpenAPIType.ARRAY),
    # litestar types,
    # the following is a hack -https://www.openapis.org/blog/2021/02/16/migrating-from-openapi-3-0-to-3-1-0
    # the format for OA 3.1 is type + contentMediaType, for 3.0.* is type + format, we do both.
    UploadFile: Schema(
        type=OpenAPIType.STRING,
        format="binary",  # type: ignore
        content_media_type="application/octet-stream",
    ),
    # pydantic types
    **PYDANTIC_TYPE_MAP,
}


def _get_type_schema_name(value: Any) -> str:
    """Extract the schema name from a data container.

    Args:
        value: A data container

    Returns:
        A string
    """
    return cast("str", getattr(value, "__schema_name__", value.__name__))


def create_enum_schema(annotation: EnumMeta) -> Schema:
    """Create a schema instance for an enum.

    Args:
        annotation: An enum.

    Returns:
        A schema instance.
    """
    enum_values: list[str | int] = [v.value for v in annotation]  # type: ignore
    openapi_type = OpenAPIType.STRING if isinstance(enum_values[0], str) else OpenAPIType.INTEGER
    return Schema(type=openapi_type, enum=enum_values)


def create_literal_schema(annotation: Any) -> Schema:
    """Create a schema instance for a Literal.

    Args:
        annotation: An Literal annotation.

    Returns:
        A schema instance.
    """
    args = get_args(annotation)
    schema = copy(TYPE_MAP[type(args[0])])
    if len(args) > 1:
        schema.enum = args
    else:
        schema.const = args[0]
    return schema


def create_schema_for_annotation(annotation: Any) -> Schema | None:
    """Get a schema from the type mapping - if possible.

    Args:
        annotation: A type annotation.

    Returns:
        A schema instance or None.
    """

    if annotation in TYPE_MAP:
        return copy(TYPE_MAP[annotation])

    if isinstance(annotation, EnumMeta):
        return create_enum_schema(annotation)

    return None


def create_schema_for_optional_field(
    field: "SignatureField",
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, Schema],
) -> Schema:
    """Create a Schema for an optional SignatureField.

    Args:
        field: A signature field instance.
        generate_examples: Whether to generate examples if none are given.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.

    Returns:
        A schema instance.
    """
    schema_or_reference = create_schema(
        field=SignatureField.create(
            field_type=make_non_optional_union(field.field_type),
            name=field.name,
            default_value=field.default_value,
        ),
        generate_examples=generate_examples,
        plugins=plugins,
        schemas=schemas,
    )

    if isinstance(schema_or_reference, Schema) and isinstance(schema_or_reference.one_of, list):
        result: list[Schema | Reference] = schema_or_reference.one_of
    else:
        result = [schema_or_reference]

    return Schema(
        one_of=[
            Schema(type=OpenAPIType.NULL),
            *result,
        ]
    )


def create_schema_for_union_field(
    field: "SignatureField",
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, Schema],
) -> Schema:
    """Create a Schema for a union SignatureField.

    Args:
        field: A signature field instance.
        generate_examples: Whether to generate examples if none are given.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.

    Returns:
        A schema instance.
    """
    return Schema(
        one_of=sort_schemas_and_references(
            [
                create_schema(field=sub_field, generate_examples=generate_examples, plugins=plugins, schemas=schemas)
                for sub_field in field.children or []
            ]
        )
    )


def create_schema_for_object_type(
    field: "SignatureField",
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, Schema],
) -> Schema:
    """Create schema for object types (dict, Mapping, list, Sequence etc.) types.

    Args:
        field: A signature field instance.
        generate_examples: Whether to generate examples if none are given.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.

    Returns:
        A schema instance.
    """
    if field.is_mapping:
        return Schema(type=OpenAPIType.OBJECT)

    if field.is_non_string_sequence or field.is_non_string_iterable:
        items = [
            create_schema(field=sub_field, generate_examples=generate_examples, plugins=plugins, schemas=schemas)
            for sub_field in (field.children or ())
        ]

        return Schema(
            type=OpenAPIType.ARRAY,
            items=Schema(one_of=sort_schemas_and_references(items)) if len(items) > 1 else items[0],
        )

    if field.is_literal:
        return create_literal_schema(field.field_type)

    raise ImproperlyConfiguredException(
        f"Parameter '{field.name}' with type '{field.field_type}' could not be mapped to an Open API type. "
        f"This can occur if a user-defined generic type is resolved as a parameter. If '{field.name}' should "
        "not be documented as a parameter, annotate it using the `Dependency` function, e.g., "
        f"`{field.name}: ... = Dependency(...)`."
    )


def create_schema_for_builtin_generics(
    field: "SignatureField",
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, Schema],
) -> "Schema":
    """Handle builtin generic types.

    Args:
        field: A signature field instance.
        generate_examples: Whether to generate examples if none are given.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.

    Returns:
        A schema instance.
    """
    origin = get_origin_or_inner_type(field.field_type)

    if origin is ClassicPagination:
        return Schema(
            type=OpenAPIType.OBJECT,
            properties={
                "items": Schema(
                    type=OpenAPIType.ARRAY,
                    items=create_schema(
                        field=field.children[0],  # type: ignore[index]
                        generate_examples=generate_examples,
                        plugins=plugins,
                        schemas=schemas,
                    ),
                ),
                "page_size": Schema(type=OpenAPIType.INTEGER, description="Number of items per page."),
                "current_page": Schema(type=OpenAPIType.INTEGER, description="Current page number."),
                "total_pages": Schema(type=OpenAPIType.INTEGER, description="Total number of pages."),
            },
        )

    if origin is OffsetPagination:
        return Schema(
            type=OpenAPIType.OBJECT,
            properties={
                "items": Schema(
                    type=OpenAPIType.ARRAY,
                    items=create_schema(
                        field=field.children[0],  # type: ignore[index]
                        generate_examples=generate_examples,
                        plugins=plugins,
                        schemas=schemas,
                    ),
                ),
                "limit": Schema(type=OpenAPIType.INTEGER, description="Maximal number of items to send."),
                "offset": Schema(type=OpenAPIType.INTEGER, description="Offset from the beginning of the query."),
                "total": Schema(type=OpenAPIType.INTEGER, description="Total number of items."),
            },
        )

    cursor_schema = create_schema(
        field=field.children[0], generate_examples=False, plugins=plugins, schemas=schemas  # type: ignore[index]
    )
    cursor_schema.description = "Unique ID, designating the last identifier in the given data set. This value can be used to request the 'next' batch of records."

    return Schema(
        type=OpenAPIType.OBJECT,
        properties={
            "items": Schema(
                type=OpenAPIType.ARRAY,
                items=create_schema(
                    field=field.children[1],  # type: ignore[index]
                    generate_examples=generate_examples,
                    plugins=plugins,
                    schemas=schemas,
                ),
            ),
            "cursor": cursor_schema,
            "results_per_page": Schema(type=OpenAPIType.INTEGER, description="Maximal number of items to send."),
        },
    )


def create_schema_for_pydantic_model(
    field_type: type[BaseModel],
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, Schema],
) -> Schema:
    """Create a schema object for a given pydantic model class.

    Args:
        field_type: A pydantic model class.
        generate_examples: Whether to generate examples if none are given.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.

    Returns:
        A schema instance.
    """
    field_type_hints = get_type_hints(field_type, include_extras=False)
    return Schema(
        required=[field.alias or field.name for field in field_type.__fields__.values() if field.required],
        properties={
            (f.alias or f.name): create_schema(
                field=SignatureField.create(field_type=field_type_hints[f.name], name=f.alias or f.name),
                generate_examples=generate_examples,
                plugins=plugins,
                schemas=schemas,
            )
            for f in field_type.__fields__.values()
        },
        type=OpenAPIType.OBJECT,
        title=_get_type_schema_name(field_type),
        description=getdoc(field_type) or None,
    )


def create_schema_for_dataclass(
    field_type: type[DataclassProtocol],
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, Schema],
) -> Schema:
    """Create a schema object for a given dataclass class.

    Args:
        field_type: A dataclass class.
        generate_examples: Whether to generate examples if none are given.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.

    Returns:
        A schema instance.
    """
    return Schema(
        required=[
            field.name for field in fields(field_type) if field.default is MISSING and field.default_factory is MISSING
        ],
        properties={
            k: create_schema(
                field=SignatureField.create(field_type=v, name=k),
                generate_examples=generate_examples,
                plugins=plugins,
                schemas=schemas,
            )
            for k, v in get_type_hints(field_type, include_extras=False).items()
        },
        type=OpenAPIType.OBJECT,
        title=_get_type_schema_name(field_type),
        description=getdoc(field_type) or None,
    )


def create_schema_for_typed_dict(
    field_type: TypedDictClass,
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, Schema],
) -> Schema:
    """Create a schema object for a given typed dict.

    Args:
        field_type: A typed-dict class.
        generate_examples: Whether to generate examples if none are given.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.

    Returns:
        A schema instance.
    """
    return Schema(
        required=list(getattr(field_type, "__required_keys__", [])),
        properties={
            k: create_schema(
                field=SignatureField.create(field_type=v, name=k),
                generate_examples=generate_examples,
                plugins=plugins,
                schemas=schemas,
            )
            for k, v in get_type_hints(field_type, include_extras=False).items()
        },
        type=OpenAPIType.OBJECT,
        title=_get_type_schema_name(field_type),
        description=getdoc(field_type) or None,
    )


def create_schema_for_plugin(
    field: "SignatureField",
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, Schema],
    plugin: OpenAPISchemaPluginProtocol,
) -> Schema | Reference:
    """Create a schema using a plugin.

    Args:
        field: A signature field instance.
        generate_examples: Whether to generate examples if none are given.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.
        plugin: A plugin for the field type.

    Returns:
        A schema instance.
    """

    schema: Schema | Reference = plugin.to_openapi_schema(field.field_type)
    if isinstance(schema, SchemaDataContainer):
        return create_schema(
            field=SignatureField.create(
                field_type=schema.data_container,
                name=field.name,
                default_value=field.default_value,
                extra=field.extra,
                kwarg_model=field.kwarg_model,
            ),
            generate_examples=generate_examples,
            plugins=plugins,
            schemas=schemas,
        )
    return schema  # pragma: no cover


def _process_schema_result(
    field: "SignatureField",
    schema: Schema,
    generate_examples: bool,
    schemas: dict[str, Schema],
) -> Schema | Reference:
    if field.kwarg_model and field.is_const and not field.is_empty and schema.const is None:
        schema.const = field.default_value

    if field.kwarg_model:
        for kwarg_model_key, schema_key in KWARG_MODEL_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP.items():
            if (value := getattr(field.kwarg_model, kwarg_model_key, Empty)) and (
                not isinstance(value, Hashable) or value not in UNDEFINED_SENTINELS
            ):
                setattr(schema, schema_key, value)

    if not schema.examples and generate_examples:
        schema.examples = create_examples_for_field(field=field)

    if schema.title and schema.type in (OpenAPIType.OBJECT, OpenAPIType.ARRAY):
        if schema.title in schemas and hash(schemas[schema.title]) != hash(schema):
            raise ImproperlyConfiguredException(
                f"Two different schemas with the title {schema.title} have been defined.\n\n"
                f"first: {encode_json(schemas[schema.title].to_schema()).decode()}\n"
                f"second: {encode_json(schema.to_schema()).decode()}\n\n"
                f"To fix this issue, either rename the base classes from which these titles are derived or manually"
                f"set a 'title' kwarg in the route handler."
            )
        schemas[schema.title] = schema
        return Reference(ref=f"#/components/schemas/{schema.title}")
    return schema


def create_schema(
    field: "SignatureField",
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, Schema],
) -> Schema | Reference:
    """Create a Schema for a given SignatureField.

    Args:
        field: A signature field instance.
        generate_examples: Whether to generate examples if none are given.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.

    Returns:
        A schema instance.
    """
    if field.is_optional:
        result: Schema | Reference = create_schema_for_optional_field(
            field=field, generate_examples=generate_examples, plugins=plugins, schemas=schemas
        )

    elif field.is_union:
        result = create_schema_for_union_field(
            field=field, generate_examples=generate_examples, plugins=plugins, schemas=schemas
        )

    elif is_pydantic_model_class(annotation=field.field_type):
        result = create_schema_for_pydantic_model(
            field_type=field.field_type, generate_examples=generate_examples, plugins=plugins, schemas=schemas
        )

    elif is_dataclass_class(annotation=field.field_type):
        result = create_schema_for_dataclass(
            field_type=field.field_type, generate_examples=generate_examples, plugins=plugins, schemas=schemas
        )

    elif is_typed_dict(annotation=field.field_type):
        result = create_schema_for_typed_dict(
            field_type=field.field_type, generate_examples=generate_examples, plugins=plugins, schemas=schemas
        )

    elif plugins_for_annotation := [plugin for plugin in plugins if plugin.is_plugin_supported_type(field.field_type)]:
        result = create_schema_for_plugin(
            field=field,
            generate_examples=generate_examples,
            plugins=plugins,
            schemas=schemas,
            plugin=plugins_for_annotation[0],
        )

    elif is_pydantic_constrained_field(field.field_type):
        result = create_constrained_field_schema(
            field_type=field.field_type, children=field.children, plugins=plugins, schemas=schemas
        )

    elif field.children and not field.is_generic:
        result = create_schema_for_object_type(
            field=field, generate_examples=generate_examples, plugins=plugins, schemas=schemas
        )

    elif field.is_generic and (
        get_origin_or_inner_type(field.field_type) in (ClassicPagination, CursorPagination, OffsetPagination)
    ):
        result = create_schema_for_builtin_generics(
            field=field, generate_examples=generate_examples, plugins=plugins, schemas=schemas
        )
    else:
        result = create_schema_for_annotation(annotation=field.field_type) or Schema()

    if isinstance(result, Reference):
        return result

    return _process_schema_result(field=field, schema=result, generate_examples=generate_examples, schemas=schemas)
