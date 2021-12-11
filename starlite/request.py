import json
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Dict, List, Union, cast

from pydantic.error_wrappers import ValidationError
from pydantic.fields import ModelField
from starlette.requests import Request

from starlite.enums import HttpMethod, MediaType
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.response import Response

if TYPE_CHECKING:  # pragma: no cover
    from starlite.routing import RouteHandler


def parse_query_params(request: Request) -> Dict[str, Any]:
    """
    Parses and normalize a given request's query parameters into a regular dictionary

    supports list query params
    """
    params: Dict[str, Union[str, List[str]]] = {}
    for key, value in request.query_params.multi_items():
        if value.replace(".", "").isnumeric():
            value = float(value) if "." in value else int(value)
        elif value in ["True", "true"]:
            value = True
        elif value in ["False", "false"]:
            value = False
        param = params.get(key)
        if param:
            if isinstance(param, str):
                params[key] = [param, value]
            else:
                params[key] = [*cast(list, param), value]
        else:
            params[key] = value
    return params


async def get_kwargs_from_request(request: Request, fields: Dict[str, ModelField]) -> Dict[str, Any]:
    """
    Given a function's signature Model fields,
    determine whether it requires the request, headers or data and return these as kwargs.
    """
    kwargs: Dict[str, Any] = {}
    if "request" in fields:
        kwargs["request"] = request
    if "headers" in fields:
        kwargs["headers"] = dict(request.headers.items())
    if "data" in fields:
        if request.method.lower() == HttpMethod.GET:
            raise ImproperlyConfiguredException("'data' kwarg is unsupported for GET requests")
        kwargs["data"] = json.loads(await request.json())
    return kwargs


async def get_http_handler_parameters(route_handler: "RouteHandler", request: Request) -> Dict[str, Any]:
    """
    Parse a given http handler function and return values matching function parameter keys
    """

    model = route_handler.get_signature_model()
    base_kwargs: Dict[str, Any] = {**parse_query_params(request=request), **request.path_params}

    try:
        # dependency injection
        dependencies: Dict[str, Any] = {}
        for key, injected in route_handler.resolve_dependencies().items():
            if key in model.__fields__:
                injected_model = injected.get_signature_model()
                injected_kwargs = await get_kwargs_from_request(request=request, fields=injected_model.__fields__)
                value = injected(**injected_model(**base_kwargs, **injected_kwargs).dict())
                if isawaitable(value):
                    value = await value
                dependencies[key] = value
        model_kwargs = await get_kwargs_from_request(request=request, fields=model.__fields__)
        return model(**model_kwargs, **base_kwargs, **dependencies).dict()
    except ValidationError as e:
        raise ValidationException(e, request) from e


async def handle_request(route_handler: "RouteHandler", request: Request) -> Response:
    """
    Handles a given request by both calling the passed in function,
    and parsing the RouteHandler stored as an attribute on it.
    """
    response_class = route_handler.response_class or Response

    params = await get_http_handler_parameters(route_handler=route_handler, request=request)
    data = route_handler(**params)

    if isawaitable(data):
        data = await data

    media_type = route_handler.media_type or response_class.media_type or MediaType.JSON
    return response_class(
        content=data,
        headers=route_handler.response_headers,
        status_code=route_handler.status_code,
        media_type=media_type,
    )
