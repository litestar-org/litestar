import json
from copy import deepcopy
from inspect import isawaitable
from typing import (  # type: ignore
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
    _UnionGenericAlias,
    cast,
)

from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError as PydanticValidationError
from pydantic.fields import ModelField
from starlette.requests import Request
from typing_extensions import Type

from starlite.enums import HttpMethod, MediaType
from starlite.exceptions import ImproperlyConfiguredException, ValidationError
from starlite.response import Response
from starlite.utils.models import set_field_optional

if TYPE_CHECKING:
    from starlite.routing import RouteHandler

T = TypeVar("T", bound=Type[BaseModel])


class Partial(Generic[T]):
    def __class_getitem__(cls, item: T) -> T:
        """
        Modifies a given T subclass of BaseModel to be all optional
        """
        item_copy = deepcopy(item)
        for field_name, field_type in item_copy.__annotations__.items():
            # we modify the field annotations to make it optional
            if not isinstance(field_type, _UnionGenericAlias) or type(None) not in field_type.__args__:
                item_copy.__annotations__[field_name] = Optional[field_type]
        for field_name, field in item_copy.__fields__.items():
            setattr(item_copy, field_name, set_field_optional(field))
        return item_copy


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
    except PydanticValidationError as e:
        raise ValidationError(e, request) from e


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
