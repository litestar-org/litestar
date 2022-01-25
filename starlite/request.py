from contextlib import suppress
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    Mapping,
    Optional,
    TypeVar,
    Union,
    cast,
)

from orjson import JSONDecodeError, loads
from pydantic.fields import SHAPE_LIST, SHAPE_SINGLETON, ModelField, Undefined
from starlette.datastructures import FormData, Headers, UploadFile
from starlette.requests import HTTPConnection
from starlette.requests import Request as StarletteRequest
from starlette.websockets import WebSocket as StarletteWebSocket
from typing_extensions import Type

from starlite.enums import HttpMethod, RequestEncodingType
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.parsers import parse_query_params
from starlite.types import Method
from starlite.utils import SignatureModel, get_signature_model

if TYPE_CHECKING:  # pragma: no cover
    from starlite.app import Starlite
    from starlite.provide import Provide

User = TypeVar("User")
Auth = TypeVar("Auth")


class Request(StarletteRequest, Generic[User, Auth]):  # pragma: no cover
    @property
    def app(self) -> "Starlite":
        return cast("Starlite", self.scope["app"])

    @property
    def user(self) -> User:
        if "user" not in self.scope:
            raise ImproperlyConfiguredException(
                "user is not defined in scope, you should install an AuthMiddleware to set it"
            )
        return cast(User, self.scope["user"])

    @property
    def auth(self) -> Auth:
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException(
                "auth is not defined in scope, you should install an AuthMiddleware to set it"
            )
        return cast(Auth, self.scope["auth"])

    @property
    def query_params(self) -> Dict[str, Any]:  # type: ignore[override]
        return parse_query_params(self)

    @property
    def method(self) -> Method:
        return cast(Method, self.scope["method"])


class WebSocket(StarletteWebSocket, Generic[User, Auth]):  # pragma: no cover
    @property
    def app(self) -> "Starlite":
        return cast("Starlite", self.scope["app"])

    @property
    def user(self) -> User:
        if "user" not in self.scope:
            raise ImproperlyConfiguredException(
                "user is not defined in scope, you should install an AuthMiddleware to set it"
            )
        return cast(User, self.scope["user"])

    @property
    def auth(self) -> Auth:
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException(
                "auth is not defined in scope, you should install an AuthMiddleware to set it"
            )
        return cast(Auth, self.scope["auth"])

    @property
    def query_params(self) -> Dict[str, Any]:  # type: ignore[override]
        return parse_query_params(self)


def handle_multipart(media_type: RequestEncodingType, form_data: FormData, field: ModelField) -> Any:
    """
    Transforms the multidict into a regular dict, try to load json on all non-file values.

    Supports lists.
    """
    values_dict: Dict[str, Any] = {}
    for key, value in form_data.multi_items():
        if not isinstance(value, UploadFile):
            with suppress(JSONDecodeError):
                value = loads(value)
        if values_dict.get(key):
            if isinstance(values_dict[key], list):
                values_dict[key].append(value)
            else:
                values_dict[key] = [values_dict[key], value]
        else:
            values_dict[key] = value
    if media_type == RequestEncodingType.MULTI_PART:
        if field.shape is SHAPE_LIST:
            return list(values_dict.values())
        if field.shape is SHAPE_SINGLETON and field.type_ is UploadFile and values_dict:
            return list(values_dict.values())[0]
    return values_dict


async def get_request_data(request: Request, field: ModelField) -> Any:
    """Given a request, parse its data - either as json or form data and return it"""
    if request.method.upper() == HttpMethod.GET:
        raise ImproperlyConfiguredException("'data' kwarg is unsupported for GET requests")
    media_type = field.field_info.extra.get("media_type")
    if not media_type or media_type == RequestEncodingType.JSON:
        body = await request.body()
        json_data = request._json = loads(body)
        return json_data
    form_data = await request.form()
    return handle_multipart(media_type=media_type, form_data=form_data, field=field)


def get_connection_parameters(
    connection: HTTPConnection,
    field_name: str,
    field: ModelField,
    query_params: Dict[str, Any],
    header_params: Headers,
) -> Any:
    """Extract path, query, header and cookie parameters correlating to field_names from the request"""
    if field_name in connection.path_params:
        return connection.path_params[field_name]
    if field_name in query_params:
        return query_params[field_name]

    extra = field.field_info.extra
    extra_keys = set(extra.keys())
    default = field.default if field.default is not Undefined else None
    if extra_keys:
        parameter_name = None
        source: Optional[Mapping] = None
        if "query" in extra_keys and extra["query"]:
            parameter_name = extra["query"]
            source = query_params
        elif "header" in extra_keys and extra["header"]:
            parameter_name = extra["header"]
            source = header_params
        elif "cookie" in extra_keys and extra["cookie"]:
            parameter_name = extra["cookie"]
            source = connection.cookies
        if parameter_name and source:
            parameter_is_required = extra["required"]
            try:
                return source[parameter_name]
            except KeyError as e:
                if parameter_is_required and not default:
                    raise ValidationException(f"Missing required parameter {parameter_name}") from e
    return default


_reserved_field_names = {"state", "headers", "cookies", "request", "socket", "data", "query"}


async def get_model_kwargs_from_connection(  # noqa: C901
    connection: Union[WebSocket, Request], fields: Dict[str, ModelField]
) -> Dict[str, Any]:
    """
    Given a function's signature Model fields, populate its kwargs from the Request object
    """
    kwargs: Dict[str, Any] = {}
    query_params = connection.query_params
    for field_name, field in fields.items():
        if field_name in _reserved_field_names:
            if field_name == "state":
                kwargs["state"] = connection.app.state.copy()
            elif field_name == "headers":
                kwargs["headers"] = connection.headers
            elif field_name == "cookies":
                kwargs["cookies"] = connection.cookies
            elif field_name == "query":
                kwargs["query"] = query_params
            elif field_name == "request":
                if not isinstance(connection, Request):
                    raise ImproperlyConfiguredException("The 'request' kwarg is not supported with websocket handlers")
                kwargs["request"] = connection
            elif field_name == "socket":
                if not isinstance(connection, WebSocket):
                    raise ImproperlyConfiguredException("The 'socket' kwarg is not supported with http handlers")
                kwargs["socket"] = connection
            elif field_name == "data":
                if not isinstance(connection, Request):
                    raise ImproperlyConfiguredException("The 'data' kwarg is not supported with websocket handlers")
                kwargs["data"] = await get_request_data(request=connection, field=field)
        else:
            kwargs[field_name] = get_connection_parameters(
                connection=connection,
                field_name=field_name,
                field=field,
                query_params=query_params,
                header_params=connection.headers,
            )
    return kwargs


async def resolve_signature_kwargs(
    signature_model: Type[SignatureModel], connection: Union[WebSocket, Request], providers: Dict[str, "Provide"]
) -> Dict[str, Any]:
    """
    Resolve the kwargs of a given signature model, and recursively resolve all dependencies.
    """
    fields = signature_model.__fields__
    dependencies: Dict[str, Any] = {}
    for key, provider in providers.items():
        if key in fields:
            provider_signature_model = get_signature_model(provider)
            provider_kwargs = await resolve_signature_kwargs(
                signature_model=provider_signature_model, connection=connection, providers=providers
            )
            dependencies[key] = await provider(
                **provider_signature_model(**provider_kwargs).dict()  # pylint: disable=not-callable
            )
    connection_kwargs = await get_model_kwargs_from_connection(
        connection=connection, fields={k: v for k, v in fields.items() if k not in dependencies}
    )
    return {**connection_kwargs, **dependencies}
