import re
from collections import deque
from dataclasses import is_dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum, EnumMeta
from http import HTTPStatus
from inspect import Signature
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Pattern,
    Type,
    Union,
    cast,
)
from uuid import UUID

from openapi_schema_pydantic import Contact, ExternalDocumentation
from openapi_schema_pydantic import Header as OpenAPIHeader
from openapi_schema_pydantic import Info, License
from openapi_schema_pydantic import MediaType as OpenAPISchemaMediaType
from openapi_schema_pydantic import (
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Reference,
    RequestBody,
    Response,
    Responses,
    Schema,
    SecurityRequirement,
    Server,
    Tag,
)
from openapi_schema_pydantic.util import PydanticSchema
from pydantic import (
    UUID1,
    UUID3,
    UUID4,
    UUID5,
    AnyHttpUrl,
    AnyUrl,
    BaseModel,
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
    create_model,
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
    is_optional,
    is_pydantic_model,
    is_union,
)
from starlette.routing import get_name

from starlite.enums import MediaType as RouteHandlerMediaType
from starlite.enums import OpenAPIMediaType
from starlite.exceptions import HTTPException, ValidationException
from starlite.handlers import RouteHandler
from starlite.params import Header
from starlite.request import create_function_signature_model

if TYPE_CHECKING:  # pragma: no cover
    from starlite.routing import Route

CAPITAL_LETTERS_PATTERN = re.compile(r"(?=[A-Z])")


def pascal_case_to_text(s: str) -> str:
    """Given a PascalCased string, return its split form- 'Pascal Cased'"""
    return " ".join(re.split(CAPITAL_LETTERS_PATTERN, s)).strip()


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
    schema = Schema(type=OpenAPIType.INTEGER if issubclass(field_type, int) else OpenAPIType.NUMBER)
    if field_type.le is not None:
        schema.maximum = field_type.le
    if field_type.lt is not None:
        schema.exclusiveMaximum = field_type.lt
    if field_type.ge is not None:
        schema.minimum = field_type.ge
    if field_type.gt is not None:
        schema.exclusiveMinimum = field_type.gt
    if field_type.multiple_of is not None:
        schema.multipleOf = field_type.multiple_of
    return schema


def create_string_constrained_field_schema(field_type: Union[Type[ConstrainedStr], Type[ConstrainedBytes]]) -> Schema:
    """
    Create Schema from Constrained Str/Bytes field
    """
    schema = Schema(type=OpenAPIType.STRING)
    if field_type.min_length:
        schema.minLength = field_type.min_length
    if field_type.max_length:
        schema.maxLength = field_type.max_length
    if hasattr(field_type, "regex") and field_type.regex:
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
        parsed_model_field = create_parsed_model_field(field_type.item_type)
        schema.items = create_schema(parsed_model_field)
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


_dataclass_model_map: Dict[Any, Type[BaseModel]] = {}


def handle_dataclass(dataclass: Any) -> Type[BaseModel]:
    """Converts a dataclass to a pydantic model and memoizes the result"""
    if not _dataclass_model_map.get(dataclass):
        _dataclass_model_map[dataclass] = create_model_from_dataclass(dataclass)
    return _dataclass_model_map[dataclass]


def create_schema(field: ModelField, ignore_optional: bool = False) -> Schema:
    """
    Create a Schema model for a given ModelField
    """
    if is_optional(field) and not ignore_optional:
        return Schema(oneOf=[Schema(type=OpenAPIType.NULL), create_schema(field, ignore_optional=True)])
    if is_pydantic_model(field.outer_type_):
        return PydanticSchema(schema_class=field.outer_type_)
    if is_dataclass(field.outer_type_):
        return PydanticSchema(schema_class=handle_dataclass(field.outer_type_))
    if is_union(field):
        return Schema(oneOf=[create_schema(sub_field) for sub_field in field.sub_fields or []])
    field_type = field.outer_type_
    if field_type in TYPE_MAP:
        return TYPE_MAP[field_type]
    if ModelFactory.is_constrained_field(field_type):
        return create_constrained_field_schema(field_type=field_type, sub_fields=field.sub_fields)
    if isinstance(field_type, EnumMeta):
        enum_values: List[Union[str, int]] = [v.value for v in field_type]  # type: ignore
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


def create_path_parameter(path_param: str) -> Parameter:
    """Create a path parameter from the given path_param string in the format param_name:type"""
    parameter_name, type_name = tuple(path_param.split(":"))
    for key, value in TYPE_MAP.items():
        if key and (hasattr(key, "__name__") and key.__name__ == type_name):
            param_schema = value
            break
    else:
        param_schema = Schema()
    return Parameter(name=parameter_name, param_in="path", required=True, param_schema=param_schema)


def create_parameters(
    route_handler: RouteHandler, handler_fields: Dict[str, ModelField], path_parameters: List[str]
) -> List[Parameter]:
    """
    Create a list of path/query/header Parameter models for the given PathHandler
    """
    parameters: List[Parameter] = []

    ignored_fields = [
        "data",
        "request",
        "headers",
        *[path_param.split(":")[0] for path_param in path_parameters],
        *list(route_handler.resolve_dependencies().keys()),
    ]
    for f_name, field in handler_fields.items():
        if f_name not in ignored_fields:
            if isinstance(field.default, Header):
                param_in = "header"
                # for header params we assume they are always required unless marked with optional
                required = not is_optional(field)
            else:
                param_in = "query"
                required = field.required
            parameters.append(
                Parameter(name=f_name, param_in=param_in, param_schema=create_schema(field), required=required)
            )
    return parameters


def get_media_type(route_handler: RouteHandler) -> RouteHandlerMediaType:
    """
    Return a MediaType enum member for the given RouteHandler or a default value
    """
    if route_handler.media_type:
        return cast(RouteHandlerMediaType, route_handler.media_type)
    if route_handler.response_class and route_handler.response_class.media_type:
        return cast(RouteHandlerMediaType, route_handler.response_class.media_type)
    return RouteHandlerMediaType.JSON


def create_parsed_model_field(value: Type) -> ModelField:
    """Create a pydantic model with the passed in value as its sole field, and return the parsed field"""
    return create_model(
        "temp", **{"value": (value, ... if not repr(value).startswith("typing.Optional") else None)}
    ).__fields__["value"]


def create_responses(route_handler: RouteHandler, raises_validation_error: bool) -> Optional[Responses]:
    """
    Create a Response model embedded in a responses dictionary for the given RouteHandler or return None
    """
    signature = Signature.from_callable(cast(Callable, route_handler.fn))
    responses: Responses = {}
    if signature.return_annotation not in [signature.empty, None]:
        as_parsed_model_field = create_parsed_model_field(signature.return_annotation)
        response = Response(
            content={
                get_media_type(route_handler): OpenAPISchemaMediaType(
                    media_type_schema=create_schema(as_parsed_model_field)
                )
            },
            description=HTTPStatus(cast(int, route_handler.status_code)).description,
        )
    else:
        response = Response(
            content=None,
            description=HTTPStatus(cast(int, route_handler.status_code)).description,
        )
    if route_handler.response_headers:
        response.headers = {}
        for key, value in route_handler.response_headers.__fields__.items():
            response.headers[key.replace("_", "-")] = OpenAPIHeader(param_schema=create_schema(value))
    responses[str(route_handler.status_code)] = response

    exceptions = route_handler.raises or []
    if raises_validation_error and ValidationException not in exceptions:
        exceptions.append(ValidationException)
    if exceptions:
        grouped_exceptions: Dict[int, List[Type[HTTPException]]] = {}
        for exc in exceptions:
            if not grouped_exceptions.get(exc.status_code):
                grouped_exceptions[exc.status_code] = []
            grouped_exceptions[exc.status_code].append(exc)
        for status_code, exception_group in grouped_exceptions.items():
            exceptions_schemas = [
                Schema(
                    type=OpenAPIType.OBJECT,
                    required=["detail", "status_code"],
                    properties=dict(
                        status_code=Schema(type=OpenAPIType.INTEGER),
                        detail=Schema(type=OpenAPIType.STRING),
                        extra=Schema(type=OpenAPIType.OBJECT, additionalProperties=Schema()),
                    ),
                    description=pascal_case_to_text(get_name(exc)),
                    example={"status_code": status_code, "detail": HTTPStatus(status_code).phrase, "extra": {}},
                )
                for exc in exception_group
            ]
            if len(exceptions_schemas) > 1:
                schema = Schema(oneOf=exceptions_schemas)
            else:
                schema = exceptions_schemas[0]
            responses[str(status_code)] = Response(
                description=HTTPStatus(status_code).description,
                content={RouteHandlerMediaType.JSON: OpenAPISchemaMediaType(media_type_schema=schema)},
            )
    return responses or None


def create_request_body(route_handler: RouteHandler, handler_fields: Dict[str, ModelField]) -> Optional[RequestBody]:
    """
    Create a RequestBody model for the given RouteHandler or return None
    """
    if "data" in handler_fields:
        return RequestBody(
            content={
                get_media_type(route_handler): OpenAPISchemaMediaType(
                    media_type_schema=create_schema(handler_fields["data"])
                )
            }
        )
    return None


def create_path_item(route: "Route") -> PathItem:
    """
    Create a PathItem model for the given route parsing all http_methods into Operation Models
    """
    path_item = PathItem(parameters=list(map(create_path_parameter, route.path_parameters)) or None)
    for http_method, route_handler in route.route_handler_map.items():
        if route_handler.include_in_schema:
            handler_fields = create_function_signature_model(fn=cast(Callable, route_handler.fn)).__fields__
            parameters = (
                create_parameters(
                    route_handler=route_handler,
                    handler_fields=handler_fields,
                    path_parameters=route.path_parameters,
                )
                or None
            )
            raises_validation_error = bool("data" in handler_fields or path_item.parameters or parameters)
            handler_name = get_name(route_handler.fn)
            operation = Operation(
                operationId=route_handler.operation_id or handler_name,
                tags=route_handler.tags,
                summary=route_handler.summary,
                description=route_handler.description,
                deprecated=route_handler.deprecated,
                responses=create_responses(
                    route_handler=route_handler, raises_validation_error=raises_validation_error
                ),
                requestBody=create_request_body(route_handler=route_handler, handler_fields=handler_fields),
                parameters=parameters,
            )
            setattr(path_item, http_method, operation)
    return path_item


class OpenAPIConfig(BaseModel):
    # endpoint config
    schema_endpoint_url: str = "/schema"
    schema_response_media_type: OpenAPIMediaType = OpenAPIMediaType.OPENAPI_YAML

    # schema config
    title: str = "StarLite API"
    version: str = "1.0.0"
    contact: Optional[Contact] = None
    description: Optional[str] = None
    external_docs: Optional[ExternalDocumentation] = None
    license: Optional[License] = None
    security: Optional[List[SecurityRequirement]] = None
    servers: List[Server] = [Server(url="/")]
    summary: Optional[str] = None
    tags: Optional[List[Tag]] = None
    terms_of_service: Optional[AnyUrl] = None
    webhooks: Optional[Dict[str, Union[PathItem, Reference]]] = None

    def to_openapi_schema(self) -> OpenAPI:
        """Generates an OpenAPI model"""
        return OpenAPI(
            externalDocs=self.external_docs,
            security=self.security,
            servers=self.servers,
            tags=self.tags,
            webhooks=self.webhooks,
            info=Info(
                title=self.title,
                version=self.version,
                description=self.description,
                contact=self.contact,
                license=self.license,
                summary=self.summary,
                termsOfService=self.terms_of_service,
            ),
        )
