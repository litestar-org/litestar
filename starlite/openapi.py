from collections import deque
from dataclasses import is_dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum, EnumMeta
from typing import Any, Dict, List, Optional, Pattern, Type, Union
from uuid import UUID

from openapi_schema_pydantic import Header, Info
from openapi_schema_pydantic import MediaType as OpenAPIMediaType
from openapi_schema_pydantic import (
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    RequestBody,
    Response,
    Responses,
    Schema,
)
from openapi_schema_pydantic.util import PydanticSchema
from pydantic import (
    UUID1,
    UUID3,
    UUID4,
    UUID5,
    AnyHttpUrl,
    AnyUrl,
    ByteSize,
    ConstrainedBytes,
    ConstrainedDecimal,
    ConstrainedFloat,
    ConstrainedInt,
    ConstrainedList,
    ConstrainedSet,
    ConstrainedStr,
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
    SHAPE_TUPLE_ELLIPSIS,
    ModelField,
)
from pydantic_factories import ModelFactory
from pydantic_factories.utils import (
    create_model_from_dataclass,
    is_any,
    is_optional,
    is_pydantic_model,
    is_union,
)

from starlite.app import Starlite
from starlite.enums import MediaType
from starlite.handlers import RouteHandler
from starlite.request import create_function_signature_model
from starlite.routing import Route


class OpenAPIFormat(str, Enum):
    """
    Formats extracted from:
    https://datatracker.ietf.org/doc/html/draft-bhutton-json-schema-validation-00#page-13
    """

    DATE = "date"
    DATE_TIME = "date-time"
    TIME = "time"
    DURATION = "duration"
    URL = "url"
    EMAIL = "email"
    IDN_EMAIL = "idn-email"
    HOST_NAME = "hostname"
    IDN_HOST_NAME = "idn-hostname"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    URI = "uri"
    URI_REFERENCE = "uri-reference"
    URI_TEMPLATE = "uri-template"
    JSON_POINTER = "json-pointer"
    RELATIVE_JSON_POINTER = "relative-json-pointer"
    IRI = "iri-reference"
    IRI_REFERENCE = "iri-reference"
    UUID = "uuid"
    REGEX = "regex"


class OpenAPIType(str, Enum):
    ARRAY = "array"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NULL = "null"
    NUMBER = "number"
    OBJECT = "object"
    STRING = "string"


PYDANTIC_FIELD_SHAPE_MAP: Dict[int, OpenAPIType] = {
    SHAPE_LIST: OpenAPIType.ARRAY,
    SHAPE_SET: OpenAPIType.ARRAY,
    SHAPE_TUPLE_ELLIPSIS: OpenAPIType.ARRAY,
    SHAPE_SEQUENCE: OpenAPIType.ARRAY,
    SHAPE_FROZENSET: OpenAPIType.ARRAY,
    SHAPE_ITERABLE: OpenAPIType.ARRAY,
    SHAPE_DEQUE: OpenAPIType.ARRAY,
    SHAPE_DICT: OpenAPIType.OBJECT,
    SHAPE_DEFAULTDICT: OpenAPIType.OBJECT,
}

TYPE_MAP: Dict[Union[Type, None, Any], Schema] = {
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


def create_numerical_constrained_field_schema(
    field_type: Union[Type[ConstrainedFloat], Type[ConstrainedInt], Type[ConstrainedDecimal]]
) -> Schema:
    """
    Create Schema from Constrained Int/Float/Decimal field
    """
    schema = Schema(type=OpenAPIType.INTEGER if issubclass(field_type, ConstrainedInt) else OpenAPIType.NUMBER)
    if field_type.ge is not None:
        schema.minimum = field_type.ge
    if field_type.gt is not None:
        schema.exclusiveMaximum = field_type.ge
    if field_type.ge is not None:
        schema.minimum = field_type.ge
    if field_type.gt is not None:
        schema.exclusiveMinimum = field_type.ge
    if field_type.multiple_of is not None:
        schema.multipleOf = field_type.multiple_of
    return schema


def create_string_constrained_field_schema(field_type: Union[Type[ConstrainedStr], Type[ConstrainedBytes]]) -> Schema:
    """
    Create Schema from Constrained Str/Bytes field
    """
    schema = Schema(type=OpenAPIType.STRING)
    if field_type.max_length:
        schema.minLength = field_type.min_length
    if field_type.max_length:
        schema.maxLength = field_type.max_length
    if field_type.regex:
        schema.pattern = field_type.regex
    if field_type.to_lower:
        schema.description = "must be in lower case"
    return schema


def create_collection_constrained_field_schema(
    field_type: Union[Type[ConstrainedList], Type[ConstrainedSet]],
    sub_fields: Optional[List[ModelField]],
) -> Schema:
    """
    Create Schema from Constrained List/Set field
    """
    schema = Schema(type=OpenAPIType.ARRAY)
    if field_type.min_items:
        schema.minItems = field_type.min_items
    if field_type.max_items:
        schema.maxItems = field_type.max_items
    if issubclass(field_type, ConstrainedSet):
        schema.uniqueItems = True
    if sub_fields:
        schema.items = [create_schema(sub_field) for sub_field in sub_fields]
    else:
        schema.items = create_schema(field_type.item_type)
    return schema


def create_constrained_field_schema(
    field_type: Union[
        Type[ConstrainedSet],
        Type[ConstrainedList],
        Type[ConstrainedStr],
        Type[ConstrainedBytes],
        Type[ConstrainedFloat],
        Type[ConstrainedInt],
        Type[ConstrainedDecimal],
    ],
    sub_fields: Optional[List[ModelField]],
) -> Schema:
    """
    Create Schema for Pydantic Constrained fields (created using constr(), conint() etc.) or by subclassing
    """
    if issubclass(field_type, (ConstrainedFloat, ConstrainedInt, ConstrainedDecimal)):
        return create_numerical_constrained_field_schema(field_type=field_type)
    if issubclass(field_type, (ConstrainedStr, ConstrainedBytes)):
        return create_string_constrained_field_schema(field_type=field_type)
    return create_collection_constrained_field_schema(field_type=field_type, sub_fields=sub_fields)


def create_schema(field: ModelField, ignore_optional: bool = False) -> Schema:
    """
    Create a Schema model for a given ModelField
    """
    if is_any(field):
        return Schema()
    if is_optional(field) and not ignore_optional:
        return Schema(oneOf=["null", create_schema(field, ignore_optional=True)])
    if is_pydantic_model(field.outer_type_):
        return PydanticSchema(schema_class=field.outer_type_)
    if is_dataclass(field.outer_type_):
        return PydanticSchema(schema_class=create_model_from_dataclass(field.outer_type_))
    if is_union(field):
        return Schema(oneOf=[create_schema(sub_field) for sub_field in field.sub_fields or []])
    field_type = field.outer_type_
    if field_type in TYPE_MAP:
        return TYPE_MAP[field_type]
    if ModelFactory.is_constrained_field(field_type):
        return create_constrained_field_schema(field_type=field_type, sub_fields=field.sub_fields)
    if isinstance(field_type, EnumMeta):
        enum_values: List[Union[str, int]] = list(field_type)
        openapi_type = OpenAPIType.STRING if isinstance(enum_values[0], str) else OpenAPIType.INTEGER
        return Schema(type=openapi_type, enum=enum_values)
    if field.sub_fields:
        # we are dealing with complex types in this case
        # the problem here is that the Python typing system is too crude to define OpenAPI objects properly
        openapi_type = PYDANTIC_FIELD_SHAPE_MAP[field.shape]
        schema = Schema(type=openapi_type)
        if openapi_type == OpenAPIType.ARRAY:
            schema.items = [create_schema(sub_field) for sub_field in field.sub_fields]
        return schema
    return Schema()


def create_parameters(route_handler: RouteHandler, handler_fields: Dict[str, ModelField], path: str) -> List[Parameter]:
    """
    Create a list of path/query/header Parameter models for the given PathHandler
    """
    parameters: List[Parameter] = []

    ignored_fields = ["data", "request", "headers", *list(route_handler.resolve_dependencies().keys())]
    for f_name, field in handler_fields.items():
        if f_name not in ignored_fields:
            if "{" + f_name in path:
                param_in = "path"
            elif isinstance(field.default, Header):
                param_in = "header"
            else:
                param_in = "query"
            parameters.append(
                Parameter(
                    name=f_name, param_in=param_in, param_schema=create_schema(field), required=not is_optional(field)
                )
            )
    return parameters


def get_media_type(route_handler: RouteHandler) -> MediaType:
    """
    Return a MediaType enum member for the given RouteHandler or a default value
    """
    if route_handler.media_type:
        return route_handler.media_type
    if route_handler.response_class and route_handler.response_class.media_type:
        return route_handler.response_class.media_type
    return MediaType.JSON


def create_responses(route_handler: RouteHandler, handler_fields: Dict[str, ModelField]) -> Optional[Responses]:
    """
    Create a Response model embedded in a responses dictionary for the given RouteHandler or return None
    """
    if "return" in handler_fields and handler_fields["return"]:
        response = Response(
            content={
                get_media_type(route_handler): OpenAPIMediaType(
                    media_type_schema=create_schema(handler_fields["return"])
                )
            },
            description="",
        )
        if route_handler.response_headers:
            response.headers = {}
            headers = route_handler.response_headers.__fields__
            for key, value in headers.items():
                if value.alias:
                    key = value.alias
                response.headers[key] = Header(param_schema=create_schema(value))
        return {str(route_handler.status_code): response}
    return None


def get_request_body(route_handler: RouteHandler, handler_fields: Dict[str, ModelField]) -> Optional[RequestBody]:
    """
    Create a RequestBody model for the given RouteHandler or return None
    """
    if "data" in handler_fields:
        return RequestBody(
            content={
                get_media_type(route_handler): OpenAPIMediaType(media_type_schema=create_schema(handler_fields["data"]))
            }
        )
    return None


def create_path_item(route: Route) -> PathItem:
    """
    Create a PathItem model for the given route parsing all http_methods into Operation Models
    """
    path_item = PathItem()
    for http_method, route_handler in route.route_handler_map.items():
        handler_fields = create_function_signature_model(fn=route_handler, ignore_return=False).__fields__
        operation = Operation(
            operationId=route_handler.operation_id,
            tags=route_handler.tags,
            summary=route_handler.summary,
            description=route_handler.description,
            deprecated=route_handler.deprecated,
            responses=create_responses(route_handler=route_handler, handler_fields=handler_fields),
            requestBody=get_request_body(route_handler=route_handler, handler_fields=handler_fields),
            parameters=create_parameters(route_handler=route_handler, handler_fields=handler_fields, path=route.path)
            or None,
        )
        setattr(path_item, http_method, operation)
    return path_item


def create_openapi_schema(app: Starlite) -> OpenAPI:
    """
    Create OpenAPI model for the given app
    """
    info = Info(title="starlite app", version="v1.0.0")
    return OpenAPI(
        info=info,
        paths={
            route.path or "/": create_path_item(route=route) for route in app.router.routes if route.include_in_schema
        },
    )
