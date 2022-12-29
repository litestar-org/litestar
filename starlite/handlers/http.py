from enum import Enum
from inspect import Signature, isawaitable
from itertools import chain
from operator import attrgetter
from typing import (
    TYPE_CHECKING,
    Any,
    AnyStr,
    Awaitable,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Type,
    Union,
    cast,
)

from pydantic import validate_arguments
from pydantic_openapi_schema.v3_1_0 import SecurityRequirement
from typing_extensions import get_args

from starlite.constants import REDIRECT_STATUS_CODES
from starlite.datastructures import (
    CacheControlHeader,
    Cookie,
    ETag,
    Provide,
    ResponseHeader,
)
from starlite.datastructures.background_tasks import BackgroundTask, BackgroundTasks
from starlite.datastructures.response_containers import (
    File,
    Redirect,
    ResponseContainer,
)
from starlite.dto import DTO
from starlite.enums import HttpMethod, MediaType
from starlite.exceptions import (
    HTTPException,
    ImproperlyConfiguredException,
    ValidationException,
)
from starlite.handlers.base import BaseRouteHandler
from starlite.openapi.datastructures import ResponseSpec
from starlite.plugins import get_plugin_for_value
from starlite.response import FileResponse, Response
from starlite.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_304_NOT_MODIFIED,
)
from starlite.types import (
    AfterRequestHookHandler,
    AfterResponseHookHandler,
    ASGIApp,
    BeforeRequestHookHandler,
    CacheKeyBuilder,
    Empty,
    EmptyType,
    ExceptionHandlersMap,
    Guard,
    Method,
    Middleware,
    ResponseCookies,
    ResponseHeadersMap,
    ResponseType,
    TypeEncodersMap,
)
from starlite.utils import Ref, annotation_is_iterable_of_type, is_async_callable
from starlite.utils.predicates import is_class_and_subclass
from starlite.utils.sync import AsyncCallable

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.connection import Request
    from starlite.datastructures.headers import Header
    from starlite.plugins import PluginProtocol
    from starlite.types import MaybePartial  # nopycln: import # noqa: F401
    from starlite.types import AnyCallable, AsyncAnyCallable

MSG_SEMANTIC_ROUTE_HANDLER_WITH_HTTP = "semantic route handlers cannot define http_method"


def _normalize_cookies(local_cookies: FrozenSet["Cookie"], layered_cookies: FrozenSet["Cookie"]) -> List[Cookie]:
    """Given two lists of cookies, ensure the uniqueness of cookies by key and return a normalized dict ready to be set
    on the response.
    """
    sorted_set = sorted(frozenset.union(local_cookies, layered_cookies), key=attrgetter("key"))
    return [cookie for cookie in sorted_set if not cookie.documentation_only]


def _normalize_headers(headers: "ResponseHeadersMap") -> Dict[str, Any]:
    """Given a dictionary of ResponseHeader, filter them and return a dictionary of values.

    Args:
        headers: A dictionary of [ResponseHeader][starlite.datastructures.ResponseHeader] values

    Returns:
        A string keyed dictionary of normalized values
    """
    return {k: v.value for k, v in headers.items() if not v.documentation_only}


async def _normalize_response_data(data: Any, plugins: List["PluginProtocol"]) -> Any:
    """Normalize the response's data by awaiting any async values and resolving plugins.

    Args:
        data: An arbitrary value
        plugins: A list of [plugins][starlite.plugins.base.PluginProtocol]

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


def _create_response_container_handler(
    after_request: Optional["AfterRequestHookHandler"],
    cookies: FrozenSet["Cookie"],
    headers: Dict[str, Any],
    media_type: str,
    status_code: int,
) -> "AsyncAnyCallable":
    """Create a handler function for ResponseContainers."""
    normalized_headers = _normalize_headers(headers)

    async def handler(data: ResponseContainer, app: "Starlite", request: "Request", **kwargs: Any) -> "ASGIApp":
        response = data.to_response(
            app=app,
            headers={**normalized_headers, **data.headers},
            status_code=status_code,
            media_type=data.media_type or media_type,
            request=request,
        )
        response.cookies = _normalize_cookies(frozenset(data.cookies), cookies)
        return await after_request(response) if after_request else response  # type: ignore

    return handler


def _create_response_handler(
    after_request: Optional["AfterRequestHookHandler"],
    cookies: FrozenSet["Cookie"],
) -> "AsyncAnyCallable":
    """Create a handler function for Starlite Responses."""

    async def handler(data: Response, **kwargs: Any) -> "ASGIApp":
        data.cookies = _normalize_cookies(frozenset(data.cookies), cookies)
        return await after_request(data) if after_request else data  # type: ignore

    return handler


def _create_generic_asgi_response_handler(
    after_request: Optional["AfterRequestHookHandler"],
    cookies: FrozenSet["Cookie"],
) -> "AsyncAnyCallable":
    """Create a handler function for Responses."""

    async def handler(data: "ASGIApp", **kwargs: Any) -> "ASGIApp":
        if hasattr(data, "set_cookie"):
            for cookie in cookies:
                data.set_cookie(**cookie.dict)
        return await after_request(data) if after_request else data  # type: ignore

    return handler


def _create_data_handler(
    after_request: Optional["AfterRequestHookHandler"],
    background: Optional[Union["BackgroundTask", "BackgroundTasks"]],
    cookies: FrozenSet["Cookie"],
    headers: "ResponseHeadersMap",
    media_type: str,
    response_class: "ResponseType",
    return_annotation: Any,
    status_code: int,
    type_encoders: Optional[TypeEncodersMap],
) -> "AsyncAnyCallable":
    """Create a handler function for arbitrary data."""
    normalized_headers = [
        (k.lower().encode("latin-1"), str(v).encode("latin-1")) for k, v in _normalize_headers(headers).items()
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

    async def handler(data: Any, plugins: List["PluginProtocol"], **kwargs: Any) -> "ASGIApp":
        if isawaitable(data):
            data = await data

        if is_dto_annotation and not isinstance(data, DTO):
            data = return_annotation(**data) if isinstance(data, dict) else return_annotation.from_model_instance(data)

        elif is_dto_iterable_annotation and not isinstance(data[0], DTO):  # pyright: ignore
            dto_type = cast("Type[DTO]", get_args(return_annotation)[0])
            data = [
                dto_type(**datum) if isinstance(datum, dict) else dto_type.from_model_instance(datum) for datum in data
            ]

        elif plugins and not (is_dto_annotation or is_dto_iterable_annotation):
            data = await _normalize_response_data(data=data, plugins=plugins)

        return await create_response(data=data)

    return handler


def _normalize_http_method(http_methods: Union[HttpMethod, Method, List[Union[HttpMethod, Method]]]) -> Set["Method"]:
    """Normalize HTTP method(s) into a set of upper-case method names.

    Args:
        http_methods: A value for http method.

    Returns:
        A normalized set of http methods.
    """
    output: Set[str] = set()

    for method in http_methods if isinstance(http_methods, list) else [http_methods]:
        if isinstance(method, HttpMethod):
            output.add(method.value.upper())
        else:
            output.add(method.upper())

    return cast("Set[Method]", output)


def _get_default_status_code(http_methods: Set["Method"]) -> int:
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


class HTTPRouteHandler(BaseRouteHandler["HTTPRouteHandler"]):
    """HTTP Route Decorator.

    Use this decorator to decorate an HTTP handler with multiple methods.
    """

    __slots__ = (
        "_resolved_after_response",
        "_resolved_before_request",
        "_resolved_response_handler",
        "after_request",
        "after_response",
        "background",
        "before_request",
        "cache",
        "cache_control",
        "cache_key_builder",
        "content_encoding",
        "content_media_type",
        "deprecated",
        "description",
        "etag",
        "has_sync_callable",
        "http_methods",
        "include_in_schema",
        "media_type",
        "operation_id",
        "raises",
        "response_class",
        "response_cookies",
        "response_description",
        "response_headers",
        "responses",
        "security",
        "status_code",
        "summary",
        "sync_to_thread",
        "tags",
        "template_name",
        "type_encoders",
    )

    has_sync_callable: bool

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHookHandler] = None,
        after_response: Optional[AfterResponseHookHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHookHandler] = None,
        cache: Union[bool, int] = False,
        cache_control: Optional[CacheControlHeader] = None,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        etag: Optional[ETag] = None,
        exception_handlers: Optional[ExceptionHandlersMap] = None,
        guards: Optional[List[Guard]] = None,
        http_method: Union[HttpMethod, Method, List[Union[HttpMethod, Method]]],
        media_type: Optional[Union[MediaType, str]] = None,
        middleware: Optional[List[Middleware]] = None,
        name: Optional[str] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[ResponseType] = None,
        response_cookies: Optional[ResponseCookies] = None,
        response_headers: Optional[ResponseHeadersMap] = None,
        status_code: Optional[int] = None,
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: Optional[str] = None,
        content_media_type: Optional[str] = None,
        deprecated: bool = False,
        description: Optional[str] = None,
        include_in_schema: bool = True,
        operation_id: Optional[str] = None,
        raises: Optional[List[Type[HTTPException]]] = None,
        response_description: Optional[str] = None,
        responses: Optional[Dict[int, ResponseSpec]] = None,
        security: Optional[List[SecurityRequirement]] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        type_encoders: Optional["TypeEncodersMap"] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize `HTTPRouteHandler`.

        Args:
            path: A path fragment for the route handler function or a list of path fragments.
                If not given defaults to '/'
            after_request: A sync or async function executed before a [Request][starlite.connection.Request] is passed
                to any route handler. If this function returns a value, the request will not reach the route handler,
                and instead this value will be used.
            after_response: A sync or async function called after the response has been awaited. It receives the
                [Request][starlite.connection.Request] object and should not return any values.
            background: A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
                [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
                Defaults to None.
            before_request: A sync or async function called immediately before calling the route handler. Receives
                the `starlite.connection.Request` instance and any non-`None` return value is used for the response,
                bypassing the route handler.
            cache: Enables response caching if configured on the application level. Valid values are 'true' or a number
                of seconds (e.g. '120') to cache the response.
            cache_control: A `cache-control` header of type
                [CacheControlHeader][starlite.datastructures.CacheControlHeader] that will be added to the response.
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
            etag: An `etag` header of type [ETag][starlite.datastructures.ETag] that will be added to the response.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            http_method: An [http method string][starlite.types.Method], a member of the enum
                [HttpMethod][starlite.enums.HttpMethod] or a list of these that correlates to the methods the
                route handler function should handle.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            name: A string identifying the route handler.
            opt: A string keyed dictionary of arbitrary values that can be accessed in [Guards][starlite.types.Guard] or
                wherever you have access to [Request][starlite.connection.request.Request] or [ASGI Scope][starlite.types.Scope].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            responses: A dictionary of additional status codes and a description of their expected content.
                This information will be included in the OpenAPI schema
            status_code: An http status code for the response. Defaults to '200' for mixed method or 'GET', 'PUT' and
                'PATCH', '201' for 'POST' and '204' for 'DELETE'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI documentation.
                This list should describe all exceptions raised within the route handler's function/method. The Starlite
                ValidationException will be added automatically for the schema if any validation is involved.
            response_description: Text used for the route's response schema description section.
            security: A list of dictionaries that contain information about which security scheme can be used on the endpoint.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        if not http_method:
            raise ImproperlyConfiguredException("An http_method kwarg is required")

        self.http_methods = _normalize_http_method(http_methods=http_method)
        self.status_code = status_code or _get_default_status_code(http_methods=self.http_methods)

        super().__init__(
            path,
            dependencies=dependencies,
            exception_handlers=exception_handlers,
            guards=guards,
            middleware=middleware,
            name=name,
            opt=opt,
            **kwargs,
        )

        self.after_request = AsyncCallable(after_request) if after_request else None  # type: ignore[arg-type]
        self.after_response = AsyncCallable(after_response) if after_response else None
        self.background = background
        self.before_request = AsyncCallable(before_request) if before_request else None
        self.cache = cache
        self.cache_control = cache_control
        self.cache_key_builder = cache_key_builder
        self.etag = etag
        self.media_type: Union[MediaType, str] = media_type or ""
        self.response_class = response_class
        self.response_cookies = response_cookies
        self.response_headers = response_headers
        self.sync_to_thread = sync_to_thread
        # OpenAPI related attributes
        self.content_encoding = content_encoding
        self.content_media_type = content_media_type
        self.deprecated = deprecated
        self.description = description
        self.include_in_schema = include_in_schema
        self.operation_id = operation_id
        self.raises = raises
        self.response_description = response_description
        self.summary = summary
        self.tags = tags
        self.type_encoders = type_encoders
        self.security = security
        self.responses = responses
        # memoized attributes, defaulted to Empty
        self._resolved_after_response: Union[Optional[AfterResponseHookHandler], EmptyType] = Empty
        self._resolved_before_request: Union[Optional[BeforeRequestHookHandler], EmptyType] = Empty
        self._resolved_response_handler: Union["Callable[[Any], Awaitable[ASGIApp]]", EmptyType] = Empty

    def __call__(self, fn: "AnyCallable") -> "HTTPRouteHandler":
        """Replace a function with itself."""
        self.fn = Ref["MaybePartial[AnyCallable]"](fn)
        self.signature = Signature.from_callable(fn)
        self._validate_handler_function()

        if not self.media_type:
            if self.signature.return_annotation in {str, bytes, AnyStr, Redirect, File} or any(
                is_class_and_subclass(self.signature.return_annotation, t_type) for t_type in (str, bytes)  # type: ignore
            ):
                self.media_type = MediaType.TEXT
            else:
                self.media_type = MediaType.JSON

        return self

    def resolve_response_class(self) -> Type["Response"]:
        """Return the closest custom Response class in the owner graph or the default Response class.

        This method is memoized so the computation occurs only once.

        Returns:
            The default [Response][starlite.response.Response] class for the route handler.
        """
        for layer in list(reversed(self.ownership_layers)):
            if layer.response_class is not None:
                return layer.response_class
        return Response

    def resolve_response_headers(self) -> "ResponseHeadersMap":
        """Return all header parameters in the scope of the handler function.

        Returns:
            A dictionary mapping keys to [ResponseHeader][starlite.datastructures.ResponseHeader] instances.
        """
        resolved_response_headers = {}
        for layer in self.ownership_layers:
            resolved_response_headers.update(layer.response_headers or {})
            for extra_header in ("cache_control", "etag"):
                header_model: Optional["Header"] = getattr(layer, extra_header, None)
                if header_model:
                    resolved_response_headers.update(
                        {
                            header_model.HEADER_NAME: ResponseHeader(
                                value=header_model.to_header(), documentation_only=header_model.documentation_only
                            )
                        }
                    )

        return resolved_response_headers

    def resolve_response_cookies(self) -> FrozenSet["Cookie"]:
        """Return a list of Cookie instances. Filters the list to ensure each cookie key is unique.

        Returns:
            A list of [Cookie][starlite.datastructures.Cookie] instances.
        """

        return frozenset(chain.from_iterable(layer.response_cookies or [] for layer in reversed(self.ownership_layers)))

    def resolve_before_request(self) -> Optional["BeforeRequestHookHandler"]:
        """Resolve the before_handler handler by starting from the route handler and moving up.

        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once.

        Returns:
            An optional [before request lifecycle hook handler][starlite.types.BeforeRequestHookHandler]
        """
        if self._resolved_before_request is Empty:
            before_request_handlers: List[AsyncCallable] = [
                layer.before_request for layer in self.ownership_layers if layer.before_request  # type: ignore[misc]
            ]
            self._resolved_before_request = cast(
                "Optional[BeforeRequestHookHandler]",
                before_request_handlers[-1] if before_request_handlers else None,
            )
        return self._resolved_before_request

    def resolve_after_response(self) -> Optional["AfterResponseHookHandler"]:
        """Resolve the after_response handler by starting from the route handler and moving up.

        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once.

        Returns:
            An optional [after response lifecycle hook handler][starlite.types.AfterResponseHookHandler]
        """
        if self._resolved_after_response is Empty:
            after_response_handlers: List[AsyncCallable] = [
                layer.after_response for layer in self.ownership_layers if layer.after_response  # type: ignore[misc]
            ]
            self._resolved_after_response = cast(
                "Optional[AfterResponseHookHandler]",
                after_response_handlers[-1] if after_response_handlers else None,
            )

        return cast("Optional[AfterResponseHookHandler]", self._resolved_after_response)

    def resolve_type_encoders(self) -> Optional[TypeEncodersMap]:
        """Resolve `type_encoders` by merging existing `type_encoders` from all layers.

        Returns:
            A `TypeEncodersMap` to use for this response or `None`
        """
        type_encoders: TypeEncodersMap = {}
        for layer in self.ownership_layers:
            if layer_type_encoders := layer.type_encoders:
                type_encoders.update(layer_type_encoders)
        return type_encoders or None

    def resolve_response_handler(
        self,
    ) -> Callable[[Any], Awaitable["ASGIApp"]]:
        """Resolve the response_handler function for the route handler.

        This method is memoized so the computation occurs only once.

        Returns:
            Async Callable to handle an HTTP Request
        """
        if self._resolved_response_handler is Empty:
            after_request_handlers: List[AsyncCallable] = [
                layer.after_request for layer in self.ownership_layers if layer.after_request  # type: ignore[misc]
            ]
            after_request = cast(
                "Optional[AfterRequestHookHandler]",
                after_request_handlers[-1] if after_request_handlers else None,
            )

            media_type = self.media_type.value if isinstance(self.media_type, Enum) else self.media_type
            response_class = self.resolve_response_class()
            headers = self.resolve_response_headers()
            cookies = self.resolve_response_cookies()
            type_encoders = self.resolve_type_encoders()

            if is_class_and_subclass(self.signature.return_annotation, ResponseContainer):  # type: ignore
                handler = _create_response_container_handler(
                    after_request=after_request,
                    cookies=cookies,
                    headers=headers,
                    media_type=media_type,
                    status_code=self.status_code,
                )

            elif is_class_and_subclass(self.signature.return_annotation, Response):
                handler = _create_response_handler(cookies=cookies, after_request=after_request)

            elif is_async_callable(self.signature.return_annotation) or self.signature.return_annotation in {
                ASGIApp,
                "ASGIApp",
            }:
                handler = _create_generic_asgi_response_handler(cookies=cookies, after_request=after_request)

            else:
                handler = _create_data_handler(
                    after_request=after_request,
                    background=self.background,
                    cookies=cookies,
                    headers=headers,
                    media_type=media_type,
                    response_class=response_class,
                    return_annotation=self.signature.return_annotation,
                    status_code=self.status_code,
                    type_encoders=type_encoders,
                )

            self._resolved_response_handler = handler
        return self._resolved_response_handler  # type:ignore[return-value]

    async def to_response(
        self, app: "Starlite", data: Any, plugins: List["PluginProtocol"], request: "Request"
    ) -> "ASGIApp":
        """Return a [Response][starlite.Response] from the handler by resolving and calling it.

        Args:
            app: The [Starlite][starlite.app.Starlite] app instance
            data: Either an instance of a [ResponseContainer][starlite.datastructures.ResponseContainer],
                a Response instance or an arbitrary value.
            plugins: An optional mapping of plugins
            request: A [Request][starlite.connection.request.Request] instance

        Returns:
            A Response instance
        """
        response_handler = self.resolve_response_handler()
        return await response_handler(app=app, data=data, plugins=plugins, request=request)  # type: ignore

    def _validate_handler_function(self) -> None:
        """Validate the route handler function once it is set by inspecting its return annotations."""
        super()._validate_handler_function()

        if self.signature.return_annotation is Signature.empty:
            raise ImproperlyConfiguredException(
                "A return value of a route handler function should be type annotated."
                "If your function doesn't return a value, annotate it as returning 'None'."
            )

        if (
            self.status_code < 200 or self.status_code in {HTTP_204_NO_CONTENT, HTTP_304_NOT_MODIFIED}
        ) and self.signature.return_annotation not in {None, "None"}:
            raise ImproperlyConfiguredException(
                "A status code 204, 304 or in the range below 200 does not support a response body."
                "If the function should return a value, change the route handler status code to an appropriate value.",
            )

        if (
            is_class_and_subclass(self.signature.return_annotation, Redirect)
            and self.status_code not in REDIRECT_STATUS_CODES
        ):
            raise ValidationException(
                f"Redirect responses should have one of "
                f"the following status codes: {', '.join([str(s) for s in REDIRECT_STATUS_CODES])}"
            )

        if (
            is_class_and_subclass(self.signature.return_annotation, File)
            or is_class_and_subclass(self.signature.return_annotation, FileResponse)
        ) and self.media_type in (
            MediaType.JSON,
            MediaType.HTML,
        ):
            self.media_type = MediaType.TEXT

        if "socket" in self.signature.parameters:
            raise ImproperlyConfiguredException("The 'socket' kwarg is not supported with http handlers")

        if "data" in self.signature.parameters and "GET" in self.http_methods:
            raise ImproperlyConfiguredException("'data' kwarg is unsupported for 'GET' request handlers")


route = HTTPRouteHandler


class get(HTTPRouteHandler):
    """GET Route Decorator.

    Use this decorator to decorate an HTTP handler for GET requests.
    """

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHookHandler] = None,
        after_response: Optional[AfterResponseHookHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHookHandler] = None,
        cache: Union[bool, int] = False,
        cache_control: Optional[CacheControlHeader] = None,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        etag: Optional[ETag] = None,
        exception_handlers: Optional[ExceptionHandlersMap] = None,
        guards: Optional[List[Guard]] = None,
        media_type: Optional[Union[MediaType, str]] = None,
        middleware: Optional[List[Middleware]] = None,
        name: Optional[str] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[ResponseType] = None,
        response_cookies: Optional[ResponseCookies] = None,
        response_headers: Optional[ResponseHeadersMap] = None,
        status_code: Optional[int] = None,
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: Optional[str] = None,
        content_media_type: Optional[str] = None,
        deprecated: bool = False,
        description: Optional[str] = None,
        include_in_schema: bool = True,
        operation_id: Optional[str] = None,
        raises: Optional[List[Type[HTTPException]]] = None,
        response_description: Optional[str] = None,
        responses: Optional[Dict[int, ResponseSpec]] = None,
        security: Optional[List[SecurityRequirement]] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        type_encoders: Optional["TypeEncodersMap"] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize `get`.

        Args:
            path: A path fragment for the route handler function or a list of path fragments.
                If not given defaults to '/'
            after_request: A sync or async function executed before a [Request][starlite.connection.Request] is passed
                to any route handler. If this function returns a value, the request will not reach the route handler,
                and instead this value will be used.
            after_response: A sync or async function called after the response has been awaited. It receives the
                [Request][starlite.connection.Request] object and should not return any values.
            background: A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
                [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
                Defaults to None.
            before_request: A sync or async function called immediately before calling the route handler. Receives
                the `starlite.connection.Request` instance and any non-`None` return value is used for the response,
                bypassing the route handler.
            cache: Enables response caching if configured on the application level. Valid values are 'true' or a number
                of seconds (e.g. '120') to cache the response.
            cache_control: A `cache-control` header of type
                [CacheControlHeader][starlite.datastructures.CacheControlHeader] that will be added to the response.
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
            etag: An `etag` header of type [ETag][starlite.datastructures.ETag] that will be added to the response.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            name: A string identifying the route handler.
            opt: A string keyed dictionary of arbitrary values that can be accessed in [Guards][starlite.types.Guard] or
                wherever you have access to [Request][starlite.connection.request.Request] or [ASGI Scope][starlite.types.Scope].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            responses: A dictionary of additional status codes and a description of their expected content.
                This information will be included in the OpenAPI schema
            status_code: An http status code for the response. Defaults to '200'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI documentation.
                This list should describe all exceptions raised within the route handler's function/method. The Starlite
                ValidationException will be added automatically for the schema if any validation is involved.
            response_description: Text used for the route's response schema description section.
            security: A list of dictionaries that contain information about which security scheme can be used on the endpoint.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
                       type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        if "http_method" in kwargs:
            raise ImproperlyConfiguredException(MSG_SEMANTIC_ROUTE_HANDLER_WITH_HTTP)

        super().__init__(
            after_request=after_request,
            after_response=after_response,
            background=background,
            before_request=before_request,
            cache=cache,
            cache_control=cache_control,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            dependencies=dependencies,
            deprecated=deprecated,
            description=description,
            etag=etag,
            exception_handlers=exception_handlers,
            guards=guards,
            http_method=HttpMethod.GET,
            include_in_schema=include_in_schema,
            media_type=media_type,
            middleware=middleware,
            name=name,
            operation_id=operation_id,
            opt=opt,
            path=path,
            raises=raises,
            response_class=response_class,
            response_cookies=response_cookies,
            response_description=response_description,
            response_headers=response_headers,
            responses=responses,
            security=security,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
            type_encoders=type_encoders,
            **kwargs,
        )


class head(HTTPRouteHandler):
    """HEAD Route Decorator.

    Use this decorator to decorate an HTTP handler for HEAD requests.
    """

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHookHandler] = None,
        after_response: Optional[AfterResponseHookHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHookHandler] = None,
        cache: Union[bool, int] = False,
        cache_control: Optional[CacheControlHeader] = None,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        etag: Optional[ETag] = None,
        exception_handlers: Optional[ExceptionHandlersMap] = None,
        guards: Optional[List[Guard]] = None,
        media_type: Optional[Union[MediaType, str]] = None,
        middleware: Optional[List[Middleware]] = None,
        name: Optional[str] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[ResponseType] = None,
        response_cookies: Optional[ResponseCookies] = None,
        response_headers: Optional[ResponseHeadersMap] = None,
        status_code: Optional[int] = None,
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: Optional[str] = None,
        content_media_type: Optional[str] = None,
        deprecated: bool = False,
        description: Optional[str] = None,
        include_in_schema: bool = True,
        operation_id: Optional[str] = None,
        raises: Optional[List[Type[HTTPException]]] = None,
        response_description: Optional[str] = None,
        responses: Optional[Dict[int, ResponseSpec]] = None,
        security: Optional[List[SecurityRequirement]] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        type_encoders: Optional["TypeEncodersMap"] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize `head`.

        Notes:
            - A response to a head request cannot include a body.
                See: [MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/HEAD).

        Args:
            path: A path fragment for the route handler function or a list of path fragments.
                If not given defaults to '/'
            after_request: A sync or async function executed before a [Request][starlite.connection.Request] is passed
                to any route handler. If this function returns a value, the request will not reach the route handler,
                and instead this value will be used.
            after_response: A sync or async function called after the response has been awaited. It receives the
                [Request][starlite.connection.Request] object and should not return any values.
            background: A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
                [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
                Defaults to None.
            before_request: A sync or async function called immediately before calling the route handler. Receives
                the `starlite.connection.Request` instance and any non-`None` return value is used for the response,
                bypassing the route handler.
            cache: Enables response caching if configured on the application level. Valid values are 'true' or a number
                of seconds (e.g. '120') to cache the response.
            cache_control: A `cache-control` header of type
                [CacheControlHeader][starlite.datastructures.CacheControlHeader] that will be added to the response.
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            name: A string identifying the route handler.
            opt: A string keyed dictionary of arbitrary values that can be accessed in [Guards][starlite.types.Guard] or
                wherever you have access to [Request][starlite.connection.request.Request] or [ASGI Scope][starlite.types.Scope].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            responses: A dictionary of additional status codes and a description of their expected content.
                This information will be included in the OpenAPI schema
            status_code: An http status code for the response. Defaults to '200'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI documentation.
                This list should describe all exceptions raised within the route handler's function/method. The Starlite
                ValidationException will be added automatically for the schema if any validation is involved.
            response_description: Text used for the route's response schema description section.
            security: A list of dictionaries that contain information about which security scheme can be used on the endpoint.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        if "http_method" in kwargs:
            raise ImproperlyConfiguredException(MSG_SEMANTIC_ROUTE_HANDLER_WITH_HTTP)

        super().__init__(
            after_request=after_request,
            after_response=after_response,
            background=background,
            before_request=before_request,
            cache=cache,
            cache_control=cache_control,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            dependencies=dependencies,
            deprecated=deprecated,
            description=description,
            etag=etag,
            exception_handlers=exception_handlers,
            guards=guards,
            http_method=HttpMethod.HEAD,
            include_in_schema=include_in_schema,
            media_type=media_type,
            middleware=middleware,
            name=name,
            operation_id=operation_id,
            opt=opt,
            path=path,
            raises=raises,
            response_class=response_class,
            response_cookies=response_cookies,
            response_description=response_description,
            response_headers=response_headers,
            responses=responses,
            security=security,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
            type_encoders=type_encoders,
            **kwargs,
        )

    def _validate_handler_function(self) -> None:
        """Validate the route handler function once it is set by inspecting its return annotations."""
        super()._validate_handler_function()

        # we allow here File and FileResponse because these have special setting for head responses
        if not (
            self.signature.return_annotation in {None, "None", "FileResponse", "File"}
            or is_class_and_subclass(self.signature.return_annotation, File)
            or is_class_and_subclass(self.signature.return_annotation, FileResponse)
        ):
            raise ImproperlyConfiguredException(
                "A response to a head request should not have a body",
            )


class post(HTTPRouteHandler):
    """POST Route Decorator.

    Use this decorator to decorate an HTTP handler for POST requests.
    """

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHookHandler] = None,
        after_response: Optional[AfterResponseHookHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHookHandler] = None,
        cache: Union[bool, int] = False,
        cache_control: Optional[CacheControlHeader] = None,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        etag: Optional[ETag] = None,
        exception_handlers: Optional[ExceptionHandlersMap] = None,
        guards: Optional[List[Guard]] = None,
        media_type: Optional[Union[MediaType, str]] = None,
        middleware: Optional[List[Middleware]] = None,
        name: Optional[str] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[ResponseType] = None,
        response_cookies: Optional[ResponseCookies] = None,
        response_headers: Optional[ResponseHeadersMap] = None,
        status_code: Optional[int] = None,
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: Optional[str] = None,
        content_media_type: Optional[str] = None,
        deprecated: bool = False,
        description: Optional[str] = None,
        include_in_schema: bool = True,
        operation_id: Optional[str] = None,
        raises: Optional[List[Type[HTTPException]]] = None,
        response_description: Optional[str] = None,
        responses: Optional[Dict[int, ResponseSpec]] = None,
        security: Optional[List[SecurityRequirement]] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        type_encoders: Optional["TypeEncodersMap"] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize `post`

        Args:
            path: A path fragment for the route handler function or a list of path fragments.
                If not given defaults to '/'
            after_request: A sync or async function executed before a [Request][starlite.connection.Request] is passed
                to any route handler. If this function returns a value, the request will not reach the route handler,
                and instead this value will be used.
            after_response: A sync or async function called after the response has been awaited. It receives the
                [Request][starlite.connection.Request] object and should not return any values.
            background: A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
                [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
                Defaults to None.
            before_request: A sync or async function called immediately before calling the route handler. Receives
                the `starlite.connection.Request` instance and any non-`None` return value is used for the response,
                bypassing the route handler.
            cache: Enables response caching if configured on the application level. Valid values are 'true' or a number
                of seconds (e.g. '120') to cache the response.
            cache_control: A `cache-control` header of type
                [CacheControlHeader][starlite.datastructures.CacheControlHeader] that will be added to the response.
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
            etag: An `etag` header of type [ETag][starlite.datastructures.ETag] that will be added to the response.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            name: A string identifying the route handler.
            opt: A string keyed dictionary of arbitrary values that can be accessed in [Guards][starlite.types.Guard] or
                wherever you have access to [Request][starlite.connection.request.Request] or [ASGI Scope][starlite.types.Scope].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            responses: A dictionary of additional status codes and a description of their expected content.
                This information will be included in the OpenAPI schema
            status_code: An http status code for the response. Defaults to '201' for 'POST'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI
                documentation. This list should describe all exceptions raised within the route handler's function/method.
                The Starlite ValidationException will be added automatically for the schema if any validation is involved.
            response_description: Text used for the route's response schema description section.
            security: A list of dictionaries that contain information about which security scheme can be used on the endpoint.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        if "http_method" in kwargs:
            raise ImproperlyConfiguredException(MSG_SEMANTIC_ROUTE_HANDLER_WITH_HTTP)
        super().__init__(
            after_request=after_request,
            after_response=after_response,
            background=background,
            before_request=before_request,
            cache=cache,
            cache_control=cache_control,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            dependencies=dependencies,
            deprecated=deprecated,
            description=description,
            exception_handlers=exception_handlers,
            etag=etag,
            guards=guards,
            http_method=HttpMethod.POST,
            include_in_schema=include_in_schema,
            media_type=media_type,
            middleware=middleware,
            name=name,
            operation_id=operation_id,
            opt=opt,
            path=path,
            raises=raises,
            response_class=response_class,
            response_cookies=response_cookies,
            response_description=response_description,
            response_headers=response_headers,
            responses=responses,
            security=security,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
            type_encoders=type_encoders,
            **kwargs,
        )


class put(HTTPRouteHandler):
    """PUT Route Decorator.

    Use this decorator to decorate an HTTP handler for PUT requests.
    """

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHookHandler] = None,
        after_response: Optional[AfterResponseHookHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHookHandler] = None,
        cache: Union[bool, int] = False,
        cache_control: Optional[CacheControlHeader] = None,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        etag: Optional[ETag] = None,
        exception_handlers: Optional[ExceptionHandlersMap] = None,
        guards: Optional[List[Guard]] = None,
        media_type: Optional[Union[MediaType, str]] = None,
        middleware: Optional[List[Middleware]] = None,
        name: Optional[str] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[ResponseType] = None,
        response_cookies: Optional[ResponseCookies] = None,
        response_headers: Optional[ResponseHeadersMap] = None,
        status_code: Optional[int] = None,
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: Optional[str] = None,
        content_media_type: Optional[str] = None,
        deprecated: bool = False,
        description: Optional[str] = None,
        include_in_schema: bool = True,
        operation_id: Optional[str] = None,
        raises: Optional[List[Type[HTTPException]]] = None,
        response_description: Optional[str] = None,
        responses: Optional[Dict[int, ResponseSpec]] = None,
        security: Optional[List[SecurityRequirement]] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        type_encoders: Optional["TypeEncodersMap"] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize `put`

        Args:
            path: A path fragment for the route handler function or a list of path fragments.
                If not given defaults to '/'
            after_request: A sync or async function executed before a [Request][starlite.connection.Request] is passed
                to any route handler. If this function returns a value, the request will not reach the route handler,
                and instead this value will be used.
            after_response: A sync or async function called after the response has been awaited. It receives the
                [Request][starlite.connection.Request] object and should not return any values.
            background: A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
                [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
                Defaults to None.
            before_request: A sync or async function called immediately before calling the route handler. Receives
                the `starlite.connection.Request` instance and any non-`None` return value is used for the response,
                bypassing the route handler.
            cache: Enables response caching if configured on the application level. Valid values are 'true' or a number
                of seconds (e.g. '120') to cache the response.
            cache_control: A `cache-control` header of type
                [CacheControlHeader][starlite.datastructures.CacheControlHeader] that will be added to the response.
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
            etag: An `etag` header of type [ETag][starlite.datastructures.ETag] that will be added to the response.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            name: A string identifying the route handler.
            opt: A string keyed dictionary of arbitrary values that can be accessed in [Guards][starlite.types.Guard] or
                wherever you have access to [Request][starlite.connection.request.Request] or [ASGI Scope][starlite.types.Scope].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            responses: A dictionary of additional status codes and a description of their expected content.
                This information will be included in the OpenAPI schema
            status_code: An http status code for the response. Defaults to '200'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI documentation.
                This list should describe all exceptions raised within the route handler's function/method. The Starlite
                ValidationException will be added automatically for the schema if any validation is involved.
            response_description: Text used for the route's response schema description section.
            security: A list of dictionaries that contain information about which security scheme can be used on the endpoint.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        if "http_method" in kwargs:
            raise ImproperlyConfiguredException(MSG_SEMANTIC_ROUTE_HANDLER_WITH_HTTP)
        super().__init__(
            after_request=after_request,
            after_response=after_response,
            background=background,
            before_request=before_request,
            cache=cache,
            cache_control=cache_control,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            dependencies=dependencies,
            deprecated=deprecated,
            description=description,
            exception_handlers=exception_handlers,
            etag=etag,
            guards=guards,
            http_method=HttpMethod.PUT,
            include_in_schema=include_in_schema,
            media_type=media_type,
            middleware=middleware,
            name=name,
            operation_id=operation_id,
            opt=opt,
            path=path,
            raises=raises,
            response_class=response_class,
            response_cookies=response_cookies,
            response_description=response_description,
            response_headers=response_headers,
            responses=responses,
            security=security,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
            type_encoders=type_encoders,
            **kwargs,
        )


class patch(HTTPRouteHandler):
    """PATCH Route Decorator.

    Use this decorator to decorate an HTTP handler for PATCH requests.
    """

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHookHandler] = None,
        after_response: Optional[AfterResponseHookHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHookHandler] = None,
        cache: Union[bool, int] = False,
        cache_control: Optional[CacheControlHeader] = None,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        etag: Optional[ETag] = None,
        exception_handlers: Optional[ExceptionHandlersMap] = None,
        guards: Optional[List[Guard]] = None,
        media_type: Optional[Union[MediaType, str]] = None,
        middleware: Optional[List[Middleware]] = None,
        name: Optional[str] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[ResponseType] = None,
        response_cookies: Optional[ResponseCookies] = None,
        response_headers: Optional[ResponseHeadersMap] = None,
        status_code: Optional[int] = None,
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: Optional[str] = None,
        content_media_type: Optional[str] = None,
        deprecated: bool = False,
        description: Optional[str] = None,
        include_in_schema: bool = True,
        operation_id: Optional[str] = None,
        raises: Optional[List[Type[HTTPException]]] = None,
        response_description: Optional[str] = None,
        responses: Optional[Dict[int, ResponseSpec]] = None,
        security: Optional[List[SecurityRequirement]] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        type_encoders: Optional["TypeEncodersMap"] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize `patch`.

        Args:
            path: A path fragment for the route handler function or a list of path fragments.
                If not given defaults to '/'
            after_request: A sync or async function executed before a [Request][starlite.connection.Request] is passed
                to any route handler. If this function returns a value, the request will not reach the route handler,
                and instead this value will be used.
            after_response: A sync or async function called after the response has been awaited. It receives the
                [Request][starlite.connection.Request] object and should not return any values.
            background: A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
                [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
                Defaults to None.
            before_request: A sync or async function called immediately before calling the route handler. Receives
                the `starlite.connection.Request` instance and any non-`None` return value is used for the response,
                bypassing the route handler.
            cache: Enables response caching if configured on the application level. Valid values are 'true' or a number
                of seconds (e.g. '120') to cache the response.
            cache_control: A `cache-control` header of type
                [CacheControlHeader][starlite.datastructures.CacheControlHeader] that will be added to the response.
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
            etag: An `etag` header of type [ETag][starlite.datastructures.ETag] that will be added to the response.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            name: A string identifying the route handler.
            opt: A string keyed dictionary of arbitrary values that can be accessed in [Guards][starlite.types.Guard] or
                wherever you have access to [Request][starlite.connection.request.Request] or [ASGI Scope][starlite.types.Scope].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            responses: A dictionary of additional status codes and a description of their expected content.
                This information will be included in the OpenAPI schema
            status_code: An http status code for the response. Defaults to '200'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI documentation.
                This list should describe all exceptions raised within the route handler's function/method. The Starlite
                ValidationException will be added automatically for the schema if any validation is involved.
            response_description: Text used for the route's response schema description section.
            security: A list of dictionaries that contain information about which security scheme can be used on the endpoint.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        if "http_method" in kwargs:
            raise ImproperlyConfiguredException(MSG_SEMANTIC_ROUTE_HANDLER_WITH_HTTP)
        super().__init__(
            after_request=after_request,
            after_response=after_response,
            background=background,
            before_request=before_request,
            cache=cache,
            cache_control=cache_control,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            dependencies=dependencies,
            deprecated=deprecated,
            description=description,
            etag=etag,
            exception_handlers=exception_handlers,
            guards=guards,
            http_method=HttpMethod.PATCH,
            include_in_schema=include_in_schema,
            media_type=media_type,
            middleware=middleware,
            name=name,
            operation_id=operation_id,
            opt=opt,
            path=path,
            raises=raises,
            response_class=response_class,
            response_cookies=response_cookies,
            response_description=response_description,
            response_headers=response_headers,
            responses=responses,
            security=security,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
            type_encoders=type_encoders,
            **kwargs,
        )


class delete(HTTPRouteHandler):
    """DELETE Route Decorator.

    Use this decorator to decorate an HTTP handler for DELETE requests.
    """

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHookHandler] = None,
        after_response: Optional[AfterResponseHookHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHookHandler] = None,
        cache: Union[bool, int] = False,
        cache_control: Optional[CacheControlHeader] = None,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        etag: Optional[ETag] = None,
        exception_handlers: Optional[ExceptionHandlersMap] = None,
        guards: Optional[List[Guard]] = None,
        media_type: Optional[Union[MediaType, str]] = None,
        middleware: Optional[List[Middleware]] = None,
        name: Optional[str] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[ResponseType] = None,
        response_cookies: Optional[ResponseCookies] = None,
        response_headers: Optional[ResponseHeadersMap] = None,
        status_code: Optional[int] = None,
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: Optional[str] = None,
        content_media_type: Optional[str] = None,
        deprecated: bool = False,
        description: Optional[str] = None,
        include_in_schema: bool = True,
        operation_id: Optional[str] = None,
        raises: Optional[List[Type[HTTPException]]] = None,
        response_description: Optional[str] = None,
        responses: Optional[Dict[int, ResponseSpec]] = None,
        security: Optional[List[SecurityRequirement]] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        type_encoders: Optional["TypeEncodersMap"] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize `delete`

        Args:
            path: A path fragment for the route handler function or a list of path fragments.
                If not given defaults to '/'
            after_request: A sync or async function executed before a [Request][starlite.connection.Request] is passed
                to any route handler. If this function returns a value, the request will not reach the route handler,
                and instead this value will be used.
            after_response: A sync or async function called after the response has been awaited. It receives the
                [Request][starlite.connection.Request] object and should not return any values.
            background: A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
                [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
                Defaults to None.
            before_request: A sync or async function called immediately before calling the route handler. Receives
                the `starlite.connection.Request` instance and any non-`None` return value is used for the response,
                bypassing the route handler.
            cache: Enables response caching if configured on the application level. Valid values are 'true' or a number
                of seconds (e.g. '120') to cache the response.
            cache_control: A `cache-control` header of type
                [CacheControlHeader][starlite.datastructures.CacheControlHeader] that will be added to the response.
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
            etag: An `etag` header of type [ETag][starlite.datastructures.ETag] that will be added to the response.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            name: A string identifying the route handler.
            opt: A string keyed dictionary of arbitrary values that can be accessed in [Guards][starlite.types.Guard] or
                wherever you have access to [Request][starlite.connection.request.Request] or [ASGI Scope][starlite.types.Scope].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            responses: A dictionary of additional status codes and a description of their expected content.
                This information will be included in the OpenAPI schema
            status_code: An http status code for the response. Defaults to '204'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI documentation.
                This list should describe all exceptions raised within the route handler's function/method. The Starlite
                ValidationException will be added automatically for the schema if any validation is involved.
            response_description: Text used for the route's response schema description section.
            security: A list of dictionaries that contain information about which security scheme can be used on the endpoint.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        if "http_method" in kwargs:
            raise ImproperlyConfiguredException(MSG_SEMANTIC_ROUTE_HANDLER_WITH_HTTP)
        super().__init__(
            after_request=after_request,
            after_response=after_response,
            background=background,
            before_request=before_request,
            cache=cache,
            cache_control=cache_control,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            dependencies=dependencies,
            deprecated=deprecated,
            description=description,
            etag=etag,
            exception_handlers=exception_handlers,
            guards=guards,
            http_method=HttpMethod.DELETE,
            include_in_schema=include_in_schema,
            media_type=media_type,
            middleware=middleware,
            name=name,
            operation_id=operation_id,
            opt=opt,
            path=path,
            raises=raises,
            response_class=response_class,
            response_cookies=response_cookies,
            response_description=response_description,
            response_headers=response_headers,
            responses=responses,
            security=security,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
            type_encoders=type_encoders,
            **kwargs,
        )
