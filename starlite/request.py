import json
from inspect import getfullargspec, isawaitable, signature
from typing import Any, Callable, Dict, List, Tuple, Union, cast

from pydantic import BaseModel, create_model
from starlette.requests import Request
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from typing_extensions import Type

from starlite.enums import HttpMethod, MediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.response import Response
from starlite.types import RouteHandler


def parse_query_params(request: Request) -> Dict[str, Any]:
    """
    Parses and normalize a given request's query parameters into a regular dictionary

    supports list query params
    """
    params: Dict[str, Union[str, List[str]]] = {}
    for key, value in request.query_params.multi_items():
        if value.replace(".", "").isnumeric():
            if "." in value:
                value = float(value)
            else:
                value = int(value)
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


def model_function_signature(route_handler: Callable, annotations: Dict[str, Any]) -> Type[BaseModel]:
    """
    Creates a pydantic model from a given dictionary of type annotations
    """
    handler_signature = signature(route_handler)
    field_definitions: Dict[str, Tuple[Any, Any]] = {}
    for key, value in annotations.items():
        parameter = handler_signature.parameters[key]
        if parameter.default is not handler_signature.empty:
            field_definitions[key] = (value, parameter.default)
        elif not repr(parameter.annotation).startswith("typing.Optional"):
            field_definitions[key] = (value, ...)
        else:
            field_definitions[key] = (value, None)
    return create_model("ParamModel", **field_definitions)


async def get_http_handler_parameters(route_handler: Callable, request: Request) -> Dict[str, Any]:
    """
    Parse a given http handler function and return values matching function parameter keys
    """

    annotations = getfullargspec(route_handler).annotations

    include_request = False
    if "request" in annotations:
        del annotations["request"]
        include_request = True

    model = model_function_signature(route_handler=route_handler, annotations=annotations)
    model_kwargs: Dict[str, Any] = {**parse_query_params(request=request), **request.path_params}

    if "data" in annotations:
        if request.method.lower() == HttpMethod.GET:
            raise ImproperlyConfiguredException("'data' kwarg is unsupported for GET http handlers")
        model_kwargs["data"] = json.loads(await request.json())

    if "headers" in annotations:
        model_kwargs["headers"] = dict(request.headers.items())

    parameters = model(**model_kwargs).dict()

    if include_request:
        parameters["request"] = request

    return parameters


def get_default_status_code(http_method: HttpMethod) -> int:
    """Return the default status code for the given http_method"""

    if http_method == HttpMethod.POST:
        return HTTP_201_CREATED
    if http_method == HttpMethod.DELETE:
        return HTTP_204_NO_CONTENT
    return HTTP_200_OK


async def handle_request(route_handler: RouteHandler, request: Request) -> Response:
    """
    Handles a given request by both calling the passed in function,
    and parsing the RouteInfo stored as an attribute on it.
    """
    response_class = route_handler.route_info.response_class or Response

    params = await get_http_handler_parameters(route_handler=route_handler, request=request)
    data = route_handler(**params)

    if isawaitable(data):
        data = await data

    status_code = route_handler.route_info.status_code or get_default_status_code(route_handler.route_info.http_method)
    media_type = route_handler.route_info.media_type or response_class.media_type or MediaType.JSON
    return response_class(
        content=data,
        headers=route_handler.route_info.response_headers,
        status_code=status_code,
        media_type=media_type,
    )
