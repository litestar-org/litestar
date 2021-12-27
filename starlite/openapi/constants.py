from collections import deque
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Pattern, Type, Union
from uuid import UUID

from openapi_schema_pydantic import Schema
from pydantic import (
    UUID1,
    UUID3,
    UUID4,
    UUID5,
    AnyHttpUrl,
    AnyUrl,
    ByteSize,
    DirectoryPath,
    EmailStr,
    FilePath,
    HttpUrl,
    IPvAnyAddress,
    IPvAnyInterface,
    IPvAnyNetwork,
    Json,
    NameEmail,
    NegativeFloat,
    NegativeInt,
    NonNegativeInt,
    NonPositiveFloat,
    PaymentCardNumber,
    PositiveFloat,
    PositiveInt,
    PostgresDsn,
    PyObject,
    RedisDsn,
    SecretBytes,
    SecretStr,
    StrictBool,
    StrictBytes,
    StrictFloat,
    StrictInt,
    StrictStr,
)
from pydantic.fields import (
    SHAPE_DEFAULTDICT,
    SHAPE_DEQUE,
    SHAPE_DICT,
    SHAPE_FROZENSET,
    SHAPE_ITERABLE,
    SHAPE_LIST,
    SHAPE_SEQUENCE,
    SHAPE_SET,
    SHAPE_TUPLE,
    SHAPE_TUPLE_ELLIPSIS,
)

from starlite.openapi.enums import OpenAPIFormat, OpenAPIType

PYDANTIC_FIELD_SHAPE_MAP: Dict[int, OpenAPIType] = {
    SHAPE_LIST: OpenAPIType.ARRAY,
    SHAPE_SET: OpenAPIType.ARRAY,
    SHAPE_TUPLE: OpenAPIType.ARRAY,
    SHAPE_TUPLE_ELLIPSIS: OpenAPIType.ARRAY,
    SHAPE_SEQUENCE: OpenAPIType.ARRAY,
    SHAPE_FROZENSET: OpenAPIType.ARRAY,
    SHAPE_ITERABLE: OpenAPIType.ARRAY,
    SHAPE_DEQUE: OpenAPIType.ARRAY,
    SHAPE_DICT: OpenAPIType.OBJECT,
    SHAPE_DEFAULTDICT: OpenAPIType.OBJECT,
}
TYPE_MAP: Dict[Union[Type[Any], None, Any], Schema] = {
    str: Schema(type=OpenAPIType.STRING),
    bool: Schema(type=OpenAPIType.BOOLEAN),
    int: Schema(type=OpenAPIType.INTEGER),
    None: Schema(type=OpenAPIType.NULL),
    float: Schema(type=OpenAPIType.NUMBER),
    dict: Schema(type=OpenAPIType.OBJECT),
    list: Schema(type=OpenAPIType.ARRAY),
    bytes: Schema(type=OpenAPIType.STRING),
    bytearray: Schema(type=OpenAPIType.STRING),
    tuple: Schema(type=OpenAPIType.ARRAY),
    set: Schema(type=OpenAPIType.ARRAY),
    frozenset: Schema(type=OpenAPIType.ARRAY),
    deque: Schema(type=OpenAPIType.ARRAY),
    UUID: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.UUID, description="Any UUID string"),
    Pattern: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.REGEX),
    # date and times
    date: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.DATE),
    datetime: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.DATE_TIME),
    timedelta: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.DURATION),
    time: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.DURATION),
    # pydantic types
    UUID1: Schema(
        type=OpenAPIType.STRING,
        schema_format=OpenAPIFormat.UUID,
        description="UUID1 string",
    ),
    UUID3: Schema(
        type=OpenAPIType.STRING,
        schema_format=OpenAPIFormat.UUID,
        description="UUID3 string",
    ),
    UUID4: Schema(
        type=OpenAPIType.STRING,
        schema_format=OpenAPIFormat.UUID,
        description="UUID4 string",
    ),
    UUID5: Schema(
        type=OpenAPIType.STRING,
        schema_format=OpenAPIFormat.UUID,
        description="UUID5 string",
    ),
    AnyHttpUrl: Schema(
        type=OpenAPIType.STRING, schema_format=OpenAPIFormat.URL, description="must be a valid HTTP based URL"
    ),
    AnyUrl: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.URL),
    ByteSize: Schema(type=OpenAPIType.INTEGER),
    DirectoryPath: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.URI_REFERENCE),
    EmailStr: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.EMAIL),
    FilePath: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.URI_REFERENCE),
    HttpUrl: Schema(
        type=OpenAPIType.STRING,
        schema_format=OpenAPIFormat.URL,
        description="must be a valid HTTP based URL",
        maxLength=2083,
    ),
    IPvAnyAddress: Schema(
        oneOf=[
            Schema(
                type=OpenAPIType.STRING,
                schema_format=OpenAPIFormat.IPV4,
                description="IPv4 address",
            ),
            Schema(
                type=OpenAPIType.STRING,
                schema_format=OpenAPIFormat.IPV4,
                description="IPv6 address",
            ),
        ]
    ),
    IPvAnyInterface: Schema(
        oneOf=[
            Schema(
                type=OpenAPIType.STRING,
                schema_format=OpenAPIFormat.IPV4,
                description="IPv4 interface",
            ),
            Schema(
                type=OpenAPIType.STRING,
                schema_format=OpenAPIFormat.IPV4,
                description="IPv6 interface",
            ),
        ]
    ),
    IPvAnyNetwork: Schema(
        oneOf=[
            Schema(
                type=OpenAPIType.STRING,
                schema_format=OpenAPIFormat.IPV4,
                description="IPv4 network",
            ),
            Schema(
                type=OpenAPIType.STRING,
                schema_format=OpenAPIFormat.IPV4,
                description="IPv6 network",
            ),
        ]
    ),
    Json: Schema(type=OpenAPIType.OBJECT, schema_format=OpenAPIFormat.JSON_POINTER),
    NameEmail: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.EMAIL, description="Name and email"),
    NegativeFloat: Schema(type=OpenAPIType.NUMBER, exclusiveMaximum=0.0),
    NegativeInt: Schema(type=OpenAPIType.INTEGER, exclusiveMaximum=0),
    NonNegativeInt: Schema(type=OpenAPIType.INTEGER, minimum=0),
    NonPositiveFloat: Schema(type=OpenAPIType.NUMBER, maximum=0.0),
    PaymentCardNumber: Schema(type=OpenAPIType.STRING, minLength=12, maxLength=19),
    PositiveFloat: Schema(type=OpenAPIType.NUMBER, exclusiveMinimum=0.0),
    PositiveInt: Schema(type=OpenAPIType.INTEGER, exclusiveMinimum=0),
    PostgresDsn: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.URI, description="postgres DSN"),
    PyObject: Schema(
        type=OpenAPIType.STRING,
        description="dot separated path identifying a python object, e.g. 'decimal.Decimal'",
    ),
    RedisDsn: Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.URI, description="redis DSN"),
    SecretBytes: Schema(type=OpenAPIType.STRING),
    SecretStr: Schema(type=OpenAPIType.STRING),
    StrictBool: Schema(type=OpenAPIType.BOOLEAN),
    StrictBytes: Schema(type=OpenAPIType.STRING),
    StrictFloat: Schema(type=OpenAPIType.NUMBER),
    StrictInt: Schema(type=OpenAPIType.INTEGER),
    StrictStr: Schema(type=OpenAPIType.STRING),
}


PYDANTIC_TO_OPENAPI_PROPERTY_MAP: Dict[str, str] = {
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
}

EXTRA_TO_OPENAPI_PROPERTY_MAP: Dict[str, str] = {
    "examples": "examples",
    "external_docs": "externalDocs",
    "content_encoding": "contentEncoding",
}
