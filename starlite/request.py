from enum import Enum
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Dict, Generic, List, TypeVar, Union, cast

from orjson import loads
from pydantic.error_wrappers import ValidationError, display_errors
from pydantic.fields import SHAPE_LIST, SHAPE_SINGLETON, ModelField
from pydantic.typing import AnyCallable
from starlette.datastructures import UploadFile
from starlette.requests import Request as StarletteRequest
from starlette.responses import FileResponse, RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse

from starlite.controller import Controller
from starlite.enums import HttpMethod, RequestEncodingType
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.types import File, Redirect, Stream

if TYPE_CHECKING:  # pragma: no cover
    from starlite.app import Starlite
    from starlite.handlers import RouteHandler

User = TypeVar("User")
Auth = TypeVar("Auth")


class Request(StarletteRequest, Generic[User, Auth]):
    @property
    def app(self) -> "Starlite":
        return cast("Starlite", self.scope["app"])

    @property
    def user(self) -> User:
        assert "user" in self.scope, "user is not defined in scope, you should install an AuthMiddleware to set it"
        return cast(User, self.scope["user"])

    @property
    def auth(self) -> Auth:
        assert "auth" in self.scope, "auth is not defined in scope, you should install an AuthMiddleware to set it"
        return cast(Auth, self.scope["auth"])


def parse_query_params(request: Request) -> Dict[str, Any]:
    """
    Parses and normalize a given request's query parameters into a regular dictionary

    supports list query params
    """
    params: Dict[str, Union[str, List[str]]] = {}
    try:
        for key, value in request.query_params.multi_items():
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
    as_dict = dict(form_data.multi_items())
    if media_type == RequestEncodingType.MULTI_PART:
        if field.shape is SHAPE_LIST:
            return list(as_dict.values())
        if field.shape is SHAPE_SINGLETON and field.type_ is UploadFile and as_dict:
            return list(as_dict.values())[0]
    return as_dict


def get_request_parameters(
    request: Request,
    field_name: str,
    field: ModelField,
    query_params: Dict[str, Any],
    header_params: Dict[str, Any],
) -> Any:
    """Extract path, query, header and cookie parameters correlating to field_names from the request"""
    if field_name in request.path_params:
        return request.path_params[field_name]
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
        source = request.cookies
    if parameter_name and source:
        parameter_is_required = extra["required"]
        try:
            return source[parameter_name]
        except KeyError as e:
            if parameter_is_required:
                raise ValidationException(f"Missing required parameter {parameter_name}") from e
    return None


async def get_model_kwargs_from_request(request: Request, fields: Dict[str, ModelField]) -> Dict[str, Any]:
    """
    Given a function's signature Model fields, populate its kwargs from the Request object
    """
    kwargs: Dict[str, Any] = {}
    query_params = parse_query_params(request=request)
    header_params = dict(request.headers.items())
    for field_name, field in fields.items():
        if field_name == "request":
            kwargs["request"] = request
        elif field_name == "headers":
            kwargs["headers"] = header_params
        elif field_name == "cookies":
            kwargs["cookies"] = request.cookies
        elif field_name == "query":
            kwargs["query"] = query_params
        elif field_name == "data":
            kwargs["data"] = await get_request_data(request=request, field=field)
        else:
            kwargs[field_name] = get_request_parameters(
                request=request,
                field_name=field_name,
                field=field,
                query_params=query_params,
                header_params=header_params,
            )
    return kwargs


async def get_http_handler_parameters(route_handler: "RouteHandler", request: Request) -> Dict[str, Any]:
    """
    Parse a given http handler function and return values matching function parameter keys
    """
    model = route_handler.signature_model
    assert model, "route handler has no signature model"
    try:
        # dependency injection
        dependencies: Dict[str, Any] = {}
        for key, provider in route_handler.resolve_dependencies().items():
            provider_kwargs = await get_model_kwargs_from_request(
                request=request, fields=provider.signature_model.__fields__
            )
            value = provider(**provider.signature_model(**provider_kwargs).dict())
            if isawaitable(value):
                value = await value
            dependencies[key] = value
        model_kwargs = await get_model_kwargs_from_request(
            request=request, fields={k: v for k, v in model.__fields__.items() if k not in dependencies}
        )
        # we return the model's attributes as a dict in order to preserve any nested models
        fields = list(model.__fields__.keys())
        return {key: model(**model_kwargs, **dependencies).__getattribute__(key) for key in fields}
    except ValidationError as e:
        raise ValidationException(
            detail=f"Validation failed for {request.method} {request.url}:\n\n{display_errors(e.errors())}"
        ) from e


async def handle_request(route_handler: "RouteHandler", request: Request) -> StarletteResponse:
    """
    Handles a given request by both calling the passed in function,
    and parsing the RouteHandler stored as an attribute on it.
    """
    params = await get_http_handler_parameters(route_handler=route_handler, request=request)

    for guard in route_handler.resolve_guards():
        result = guard(request, route_handler.copy())
        if isawaitable(result):
            await result

    endpoint = cast(AnyCallable, route_handler.fn)

    if isinstance(route_handler.owner, Controller):
        data = endpoint(route_handler.owner, **params)
    else:
        data = endpoint(**params)
    if isawaitable(data):
        data = await data
    if isinstance(data, StarletteResponse):
        return data

    status_code = cast(int, route_handler.status_code)
    headers = {k: v.value for k, v in route_handler.resolve_response_headers().items()}
    if isinstance(data, Redirect):
        return RedirectResponse(headers=headers, status_code=status_code, url=data.path)

    media_type = (
        route_handler.media_type.value if isinstance(route_handler.media_type, Enum) else route_handler.media_type
    )
    if isinstance(data, File):
        return FileResponse(media_type=media_type, headers=headers, **data.dict())
    if isinstance(data, Stream):
        return StreamingResponse(content=data.iterator, status_code=status_code, media_type=media_type, headers=headers)

    response_class = route_handler.resolve_response_class()
    return response_class(
        headers=headers,
        status_code=status_code,
        content=data,
        media_type=media_type,
    )
