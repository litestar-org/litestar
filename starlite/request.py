from contextlib import suppress
from typing import TYPE_CHECKING, Any, Dict, Generic, List, TypeVar, Union, cast

from orjson import JSONDecodeError, loads
from pydantic.fields import SHAPE_LIST, SHAPE_SINGLETON, ModelField
from starlette.datastructures import FormData, UploadFile
from starlette.requests import HTTPConnection
from starlette.requests import Request as StarletteRequest
from starlette.websockets import WebSocket as StarletteWebSocket

from starlite.enums import HttpMethod, RequestEncodingType
from starlite.exceptions import ImproperlyConfiguredException, ValidationException

if TYPE_CHECKING:  # pragma: no cover
    from starlite.app import Starlite

User = TypeVar("User")
Auth = TypeVar("Auth")


class Request(StarletteRequest, Generic[User, Auth]):
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


class WebSocket(StarletteWebSocket, Generic[User, Auth]):
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


def parse_query_params(connection: HTTPConnection) -> Dict[str, Any]:
    """
    Parses and normalize a given connection's query parameters into a regular dictionary

    Extends the Starlette query params handling by supporting lists
    """
    params: Dict[str, Union[str, List[str]]] = {}
    try:
        for key, value in connection.query_params.multi_items():
            if value in ["True", "true"]:
                value = True  # type: ignore
            elif value in ["False", "false"]:
                value = False  # type: ignore
            param = params.get(key)
            if param:
                if isinstance(param, str):
                    params[key] = [param, value]
                else:
                    params[key] = [*cast(List[Any], param), value]
            else:
                params[key] = value
        return params
    except KeyError:
        return params


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
    if request.method.lower() == HttpMethod.GET:
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
    header_params: Dict[str, Any],
) -> Any:
    """Extract path, query, header and cookie parameters correlating to field_names from the request"""
    if field_name in connection.path_params:
        return connection.path_params[field_name]
    if field_name in query_params:
        return query_params[field_name]

    extra = field.field_info.extra
    parameter_name = None
    source = None

    if extra.get("query"):
        parameter_name = extra["query"]
        source = query_params
    if extra.get("header"):
        parameter_name = extra["header"]
        source = header_params
    if extra.get("cookie"):
        parameter_name = extra["cookie"]
        source = connection.cookies
    if parameter_name and source:
        parameter_is_required = extra["required"]
        try:
            return source[parameter_name]
        except KeyError as e:
            if parameter_is_required:
                raise ValidationException(f"Missing required parameter {parameter_name}") from e
    return None


async def get_model_kwargs_from_connection(connection: HTTPConnection, fields: Dict[str, ModelField]) -> Dict[str, Any]:
    """
    Given a function's signature Model fields, populate its kwargs from the Request object
    """
    kwargs: Dict[str, Any] = {}
    query_params = parse_query_params(connection=connection)
    header_params = dict(connection.headers.items())
    for field_name, field in fields.items():
        if field_name == "headers":
            kwargs["headers"] = header_params
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
                header_params=header_params,
            )
    return kwargs
