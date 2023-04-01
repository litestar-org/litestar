from __future__ import annotations

from functools import lru_cache
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Sequence, cast

from typing_extensions import get_args

from litestar.dto import DTO
from litestar.enums import HttpMethod
from litestar.exceptions import ValidationException
from litestar.plugins import get_plugin_for_value
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from litestar.utils import (
    annotation_is_iterable_of_type,
    is_async_callable,
    is_class_and_subclass,
)

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import Request
    from litestar.datastructures import Cookie, ResponseHeader
    from litestar.plugins import SerializationPluginProtocol
    from litestar.response import Response
    from litestar.response_containers import ResponseContainer
    from litestar.types import (
        AfterRequestHookHandler,
        ASGIApp,
        AsyncAnyCallable,
        Method,
        ResponseType,
        TypeEncodersMap,
    )

__all__ = (
    "create_data_handler",
    "create_generic_asgi_response_handler",
    "create_response_container_handler",
    "create_response_handler",
    "filter_cookies",
    "get_default_status_code",
    "normalize_headers",
    "normalize_http_method",
    "normalize_response_data",
)


def create_data_handler(
    after_request: AfterRequestHookHandler | None,
    background: BackgroundTask | BackgroundTasks | None,
    cookies: frozenset[Cookie],
    headers: frozenset[ResponseHeader],
    media_type: str,
    response_class: ResponseType,
    return_annotation: Any,
    status_code: int,
    type_encoders: TypeEncodersMap | None,
) -> AsyncAnyCallable:
    """Create a handler function for arbitrary data.

    Args:
        after_request: An after request handler.
        background: A background task or background tasks.
        cookies: A set of pre-defined cookies.
        headers: A set of response headers.
        media_type: The response media type.
        response_class: The response class to use.
        return_annotation: The return annotation.
        status_code: The response status code.
        type_encoders: A mapping of types to encoder functions.

    Returns:
        A handler function.

    """
    normalized_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1")) for name, value in normalize_headers(headers).items()
    ]
    cookie_headers = [cookie.to_encoded_header() for cookie in cookies if not cookie.documentation_only]
    raw_headers = [*normalized_headers, *cookie_headers]
    is_dto_annotation = is_class_and_subclass(return_annotation, DTO)
    is_dto_iterable_annotation = annotation_is_iterable_of_type(return_annotation, DTO)

    async def create_response(data: Any) -> "ASGIApp":
        response = response_class(
            background=background,
            content=data,
            media_type=media_type,
            status_code=status_code,
            type_encoders=type_encoders,
        )
        response.raw_headers = raw_headers

        if after_request:
            return await after_request(response)  # type: ignore

        return response

    async def handler(data: Any, plugins: list["SerializationPluginProtocol"], **kwargs: Any) -> "ASGIApp":
        if isawaitable(data):
            data = await data

        if is_dto_annotation and not isinstance(data, DTO):
            data = return_annotation(**data) if isinstance(data, dict) else return_annotation.from_model_instance(data)

        elif is_dto_iterable_annotation and data and not isinstance(data[0], DTO):  # pyright: ignore
            dto_type = cast("type[DTO]", get_args(return_annotation)[0])
            data = [
                dto_type(**datum) if isinstance(datum, dict) else dto_type.from_model_instance(datum) for datum in data
            ]

        elif plugins and not (is_dto_annotation or is_dto_iterable_annotation):
            data = await normalize_response_data(data=data, plugins=plugins)

        return await create_response(data=data)

    return handler


def filter_cookies(local_cookies: frozenset[Cookie], layered_cookies: frozenset[Cookie]) -> list[Cookie]:
    """Given two sets of cookies, return a unique list of cookies, that are not marked as documentation_only.

    Args:
        local_cookies: Cookies returned from the local scope.
        layered_cookies: Cookies returned from the layers.

    Returns:
        A unified list of cookies
    """
    return [cookie for cookie in {*local_cookies, *layered_cookies} if not cookie.documentation_only]


def create_generic_asgi_response_handler(
    after_request: AfterRequestHookHandler | None,
    cookies: frozenset[Cookie],
) -> AsyncAnyCallable:
    """Create a handler function for Responses.

    Args:
        after_request: An after request handler.
        cookies: A set of pre-defined cookies.

    Returns:
        A handler function.
    """

    async def handler(data: "ASGIApp", **kwargs: Any) -> "ASGIApp":
        if hasattr(data, "set_cookie"):
            for cookie in cookies:
                data.set_cookie(**cookie.dict)
        return await after_request(data) if after_request else data  # type: ignore

    return handler


@lru_cache(1024)
def normalize_headers(headers: frozenset[ResponseHeader]) -> dict[str, str]:
    """Given a dictionary of ResponseHeader, filter them and return a dictionary of values.

    Args:
        headers: A dictionary of :class:`ResponseHeader <litestar.datastructures.ResponseHeader>` values

    Returns:
        A string keyed dictionary of normalized values
    """
    return {
        header.name: cast("str", header.value)  # we know value to be a string at this point because we validate it
        # that it's not None when initializing a header with documentation_only=True
        for header in headers
        if not header.documentation_only
    }


async def normalize_response_data(data: Any, plugins: list["SerializationPluginProtocol"]) -> Any:
    """Normalize the response's data by awaiting any async values and resolving plugins.

    Args:
        data: An arbitrary value
        plugins: A list of :class:`plugins <litestar.plugins.base.SerializationPluginProtocol>`
    Returns:
        Value for the response body
    """

    plugin = get_plugin_for_value(value=data, plugins=plugins)
    if not plugin:
        return data

    if is_async_callable(plugin.to_dict):
        if isinstance(data, (list, tuple)):
            return [await plugin.to_dict(datum) for datum in data]
        return await plugin.to_dict(data)

    if isinstance(data, (list, tuple)):
        return [plugin.to_dict(datum) for datum in data]
    return plugin.to_dict(data)


def create_response_container_handler(
    after_request: AfterRequestHookHandler | None,
    cookies: frozenset[Cookie],
    headers: frozenset[ResponseHeader],
    media_type: str,
    status_code: int,
) -> AsyncAnyCallable:
    """Create a handler function for ResponseContainers.

    Args:
        after_request: An after request handler.
        cookies: A set of pre-defined cookies.
        headers: A set of response headers.
        media_type: The response media type.
        status_code: The response status code.

    Returns:
        A handler function.
    """
    normalized_headers = normalize_headers(headers)

    async def handler(data: ResponseContainer, app: "Litestar", request: "Request", **kwargs: Any) -> "ASGIApp":
        response = data.to_response(
            app=app,
            headers={**normalized_headers, **data.headers},
            status_code=status_code,
            media_type=data.media_type or media_type,
            request=request,
        )
        response.cookies = filter_cookies(frozenset(data.cookies), cookies)
        return await after_request(response) if after_request else response  # type: ignore

    return handler


def create_response_handler(
    after_request: AfterRequestHookHandler | None,
    cookies: frozenset[Cookie],
) -> AsyncAnyCallable:
    """Create a handler function for Litestar Responses.

    Args:
        after_request: An after request handler.
        cookies: A set of pre-defined cookies.

    Returns:
        A handler function.
    """

    async def handler(data: Response, **kwargs: Any) -> "ASGIApp":
        data.cookies = filter_cookies(frozenset(data.cookies), cookies)
        return await after_request(data) if after_request else data  # type: ignore

    return handler


def normalize_http_method(http_methods: HttpMethod | Method | Sequence[HttpMethod | Method]) -> set[Method]:
    """Normalize HTTP method(s) into a set of upper-case method names.

    Args:
        http_methods: A value for http method.

    Returns:
        A normalized set of http methods.
    """
    output: set[str] = set()

    if isinstance(http_methods, str):
        http_methods = [http_methods]  # pyright: ignore

    for method in http_methods:
        method_name = method.value.upper() if isinstance(method, HttpMethod) else method.upper()
        if method_name not in HTTP_METHOD_NAMES:
            raise ValidationException(f"Invalid HTTP method: {method_name}")
        output.add(method_name)

    return cast("set[Method]", output)


def get_default_status_code(http_methods: set[Method]) -> int:
    """Return the default status code for a given set of HTTP methods.

    Args:
        http_methods: A set of method strings

    Returns:
        A status code
    """
    if HttpMethod.POST in http_methods:
        return HTTP_201_CREATED
    if HttpMethod.DELETE in http_methods:
        return HTTP_204_NO_CONTENT
    return HTTP_200_OK


HTTP_METHOD_NAMES = {m.value for m in HttpMethod}
