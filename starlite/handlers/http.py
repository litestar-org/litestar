# pylint: disable=too-many-instance-attributes
from contextlib import suppress
from enum import Enum
from inspect import Signature, isawaitable, isclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union, cast

from pydantic import validate_arguments
from starlette.responses import FileResponse, RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from starlite.constants import REDIRECT_STATUS_CODES
from starlite.datastructures import (
    BackgroundTask,
    BackgroundTasks,
    Cookie,
    File,
    Redirect,
    ResponseHeader,
    Stream,
    Template,
)
from starlite.enums import HttpMethod, MediaType
from starlite.exceptions import (
    HTTPException,
    ImproperlyConfiguredException,
    ValidationException,
)
from starlite.handlers.base import BaseRouteHandler
from starlite.lifecycle_hooks import (
    AfterRequestHook,
    AfterResponseHook,
    BeforeRequestHook,
)
from starlite.plugins import PluginProtocol, get_plugin_for_value
from starlite.provide import Provide
from starlite.response import Response, TemplateResponse
from starlite.types import (
    AfterRequestHandler,
    AfterResponseHandler,
    BeforeRequestHandler,
    CacheKeyBuilder,
    Empty,
    EmptyType,
    ExceptionHandler,
    Guard,
    Method,
    Middleware,
)
from starlite.utils import is_async_callable

if TYPE_CHECKING:
    from pydantic.typing import AnyCallable

    from starlite.app import Starlite


class HTTPRouteHandler(BaseRouteHandler["HTTPRouteHandler"]):
    __slots__ = (
        "_resolved_after_request",
        "_resolved_after_response",
        "_resolved_before_request",
        "_resolved_response_class",
        "_resolved_response_cookies",
        "_resolved_response_headers",
        "after_request",
        "after_response",
        "background",
        "before_request",
        "cache",
        "cache_key_builder",
        "content_encoding",
        "content_media_type",
        "deprecated",
        "description",
        "http_method",
        "include_in_schema",
        "media_type",
        "operation_id",
        "raises",
        "response_class",
        "response_cookies",
        "response_description",
        "response_headers",
        "status_code",
        "summary",
        "sync_to_thread",
        "tags",
        "template_name",
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHandler] = None,
        after_response: Optional[AfterResponseHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHandler] = None,
        cache: Union[bool, int] = False,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        http_method: Union[HttpMethod, Method, List[Union[HttpMethod, Method]]],
        media_type: Union[MediaType, str] = MediaType.JSON,
        middleware: Optional[List[Middleware]] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[Type[Response]] = None,
        response_cookies: Optional[List[Cookie]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
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
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        HTTP Route Decorator. Use this decorator to decorate an HTTP handler with multiple methods.

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
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string/[Provider][starlite.provide.Provide] dictionary that maps dependency providers.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            http_method: An [http method string][starlite.types.Method], a member of the enum
                [HttpMethod][starlite.enums.HttpMethod] or a list of these that correlates to the methods the
                route handler function should handle.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            opt: A string key dictionary of arbitrary values that can be accessed [Guards][starlite.types.Guard].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            status_code: An http status code for the response. Defaults to '200' for mixed method or 'GET', 'PUT' and
                'PATCH', '201' for 'POST' and '204' for 'DELETE'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the
                OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the
                wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI
                documentation. This list should describe all exceptions raised within the route handler's
                function/method. The Starlite ValidationException will be added automatically for the schema if
                any validation is involved.
            response_description: Text used for the route's response schema description section.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
        """
        if not http_method:
            raise ImproperlyConfiguredException("An http_method kwarg is required")
        if isinstance(http_method, list):
            self.http_method: Union[List[str], str] = [v.upper() for v in http_method]
            if len(http_method) == 1:
                self.http_method = http_method[0]
        else:
            self.http_method = http_method.value if isinstance(http_method, HttpMethod) else http_method
        if status_code:
            self.status_code = status_code
        elif self.http_method == HttpMethod.POST:
            self.status_code = HTTP_201_CREATED
        elif self.http_method == HttpMethod.DELETE:
            self.status_code = HTTP_204_NO_CONTENT
        else:
            self.status_code = HTTP_200_OK
        super().__init__(
            path=path,
            dependencies=dependencies,
            guards=guards,
            opt=opt,
            middleware=middleware,
            exception_handlers=exception_handlers,
        )
        self.after_request = after_request
        self.after_response = after_response
        self.background = background
        self.before_request = before_request
        self.cache = cache
        self.cache_key_builder = cache_key_builder
        self.media_type = media_type
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
        # memoized attributes, defaulted to Empty
        self._resolved_after_request: Union[Optional[AfterRequestHook], EmptyType] = Empty
        self._resolved_after_response: Union[Optional[AfterResponseHook], EmptyType] = Empty
        self._resolved_before_request: Union[Optional[BeforeRequestHook], EmptyType] = Empty
        self._resolved_response_headers: Union[Dict[str, ResponseHeader], EmptyType] = Empty
        self._resolved_response_cookies: Union[List[Cookie], EmptyType] = Empty
        self._resolved_response_class: Union[Type[Response], EmptyType] = Empty

    def __call__(self, fn: "AnyCallable") -> "HTTPRouteHandler":
        """
        Replaces a function with itself
        """
        self.fn = fn
        self._validate_handler_function()
        return self

    def resolve_response_class(self) -> Type[Response]:
        """
        Returns the closest custom Response class in the owner graph or the default Response class.

        This method is memoized so the computation occurs only once.
        """
        if self._resolved_response_class is Empty:
            self._resolved_response_class = Response
            for layer in self.ownership_layers:
                if layer.response_class is not None:
                    self._resolved_response_class = layer.response_class
        return cast("Type[Response]", self._resolved_response_class)

    def resolve_response_headers(self) -> Dict[str, "ResponseHeader"]:
        """
        Returns all header parameters in the scope of the handler function

        This method is memoized so the computation occurs only once.
        """
        if self._resolved_response_headers is Empty:
            self._resolved_response_headers = {}
            for layer in self.ownership_layers:
                self._resolved_response_headers.update(layer.response_headers or {})
        return cast("Dict[str, ResponseHeader]", self._resolved_response_headers)

    def resolve_response_cookies(self) -> List[Cookie]:
        """
        Returns a list of Cookie instances. Filters the list to ensure each cookie key is unique.

        This method is memoized so the computation occurs only once.
        """
        if self._resolved_response_cookies is Empty:
            self._resolved_response_cookies = []
            cookies = []
            for layer in self.ownership_layers:
                cookies.extend(layer.response_cookies or [])
            for cookie in reversed(cookies):
                if not any(cookie.key == c.key for c in self._resolved_response_cookies):
                    self._resolved_response_cookies.append(cookie)
        return cast("List[Cookie]", self._resolved_response_cookies)

    def resolve_before_request(self) -> Optional["BeforeRequestHook"]:
        """
        Resolves the before_handler handler by starting from the route handler and moving up.

        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once
        """
        if self._resolved_before_request is Empty:
            self._resolved_before_request = BeforeRequestHook.resolve_for_handler(self, "before_request")
        return cast("Optional[BeforeRequestHook]", self._resolved_before_request)

    def resolve_after_request(self) -> Optional["AfterRequestHook"]:
        """
        Resolves the after_request handler by starting from the route handler and moving up.

        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once
        """
        if self._resolved_after_request is Empty:
            self._resolved_after_request = AfterRequestHook.resolve_for_handler(self, "after_request")
        return cast("Optional[AfterRequestHook]", self._resolved_after_request)

    def resolve_after_response(self) -> Optional["AfterResponseHook"]:
        """
        Resolves the after_response handler by starting from the route handler and moving up.

        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once
        """
        if self._resolved_after_response is Empty:
            self._resolved_after_response = AfterResponseHook.resolve_for_handler(self, "after_response")
        return cast("Optional[AfterResponseHook]", self._resolved_after_response)

    @property
    def http_methods(self) -> List["Method"]:
        """
        Returns a list of the RouteHandler's HttpMethod members
        """
        return cast("List[Method]", self.http_method if isinstance(self.http_method, list) else [self.http_method])

    async def to_response(self, data: Any, app: "Starlite", plugins: List[PluginProtocol]) -> StarletteResponse:
        """
        Given a data kwarg, determine its type and return the appropriate response
        """
        if isawaitable(data):
            data = await data
        media_type = self.media_type.value if isinstance(self.media_type, Enum) else self.media_type
        headers = {k: v.value for k, v in self.resolve_response_headers().items() if not v.documentation_only}
        cookies = self.resolve_response_cookies()
        response: StarletteResponse
        if isinstance(data, (StarletteResponse, Redirect, File, Stream, Template)):
            response = self._get_response_from_data(
                app=app,
                cookies=cookies,
                data=data,
                headers=headers,
                media_type=media_type,
            )
        else:
            plugin = get_plugin_for_value(value=data, plugins=plugins)
            if plugin:
                if is_async_callable(plugin.to_dict):
                    if isinstance(data, (list, tuple)):
                        data = [await plugin.to_dict(datum) for datum in data]  # type: ignore
                    else:
                        data = await plugin.to_dict(data)  # type: ignore
                else:
                    if isinstance(data, (list, tuple)):
                        data = [plugin.to_dict(datum) for datum in data]
                    else:
                        data = plugin.to_dict(data)
            response_class = self.resolve_response_class()
            response = response_class(
                background=self.background,
                content=data,
                headers=headers,
                media_type=media_type,
                status_code=self.status_code,
            )
            for cookie in self._normalize_cookies(cookies, []):
                response.set_cookie(**cookie)
        return await self._process_after_request_hook(response)

    def _validate_handler_function(self) -> None:
        """
        Validates the route handler function once it is set by inspecting its return annotations
        """
        super()._validate_handler_function()
        signature = Signature.from_callable(cast("AnyCallable", self.fn))
        return_annotation = signature.return_annotation
        if return_annotation is Signature.empty:
            raise ValidationException(
                "A return value of a route handler function should be type annotated."
                "If your function doesn't return a value or returns None, annotate it as returning None."
            )
        if isclass(return_annotation):
            with suppress(TypeError):
                if issubclass(return_annotation, Redirect) and self.status_code not in REDIRECT_STATUS_CODES:
                    raise ValidationException(
                        f"Redirect responses should have one of "
                        f"the following status codes: {', '.join([str(s) for s in REDIRECT_STATUS_CODES])}"
                    )
                if issubclass(return_annotation, File) and self.media_type in [MediaType.JSON, MediaType.HTML]:
                    self.media_type = MediaType.TEXT
        if "socket" in signature.parameters:
            raise ImproperlyConfiguredException("The 'socket' kwarg is not supported with http handlers")
        if "data" in signature.parameters and "GET" in self.http_methods:
            raise ImproperlyConfiguredException("'data' kwarg is unsupported for 'GET' request handlers")

    @staticmethod
    def _normalize_cookies(local_cookies: List[Cookie], layered_cookies: List[Cookie]) -> List[Dict[str, Any]]:
        """
        Given two lists of cookies, ensures the uniqueness of cookies by key
        and returns a normalized dict ready to be set on the response.
        """
        filtered_cookies = [*local_cookies]
        for cookie in layered_cookies:
            if not any(cookie.key == c.key for c in filtered_cookies):
                filtered_cookies.append(cookie)
        normalized_cookies: List[Dict[str, Any]] = []
        for cookie in filtered_cookies:
            if not cookie.documentation_only:
                normalized_cookies.append(cookie.dict(exclude_none=True, exclude={"documentation_only", "description"}))
        return normalized_cookies

    def _get_response_from_data(
        self,
        app: "Starlite",
        cookies: List[Cookie],
        data: Union[StarletteResponse, Redirect, File, Stream, Template],
        headers: dict,
        media_type: Union[MediaType, str],
    ) -> StarletteResponse:
        """
        Determines the correct response type to return given data
        """
        if isinstance(data, (Redirect, File, Stream, Template)):
            headers.update(data.headers)
            normalized_cookies = self._normalize_cookies(data.cookies, cookies)
            if isinstance(data, Redirect):
                response: "StarletteResponse" = RedirectResponse(
                    headers=headers, status_code=self.status_code, url=data.path, background=data.background
                )
            elif isinstance(data, File):
                response = FileResponse(
                    background=data.background,
                    filename=data.filename,
                    headers=headers,
                    media_type=media_type,
                    path=data.path,
                    stat_result=data.stat_result,
                )
            elif isinstance(data, Stream):
                response = StreamingResponse(
                    background=data.background,
                    content=data.iterator,
                    headers=headers,
                    media_type=media_type,
                    status_code=self.status_code,
                )
            else:
                if not app.template_engine:
                    raise ImproperlyConfiguredException("Template engine is not configured")
                response = TemplateResponse(
                    background=data.background,
                    context=data.context,
                    headers=headers,
                    status_code=self.status_code,
                    template_engine=app.template_engine,
                    template_name=data.name,
                )
        elif isinstance(data, Response):
            response = data
            normalized_cookies = self._normalize_cookies(data.cookies, cookies)
        else:
            response = data
            normalized_cookies = self._normalize_cookies(cookies, [])

        for cookie in normalized_cookies:
            response.set_cookie(**cookie)

        return response

    async def _process_after_request_hook(
        self,
        response: StarletteResponse,
    ) -> StarletteResponse:
        """
        Receives a response and handles after_request, if defined.
        """
        after_request = self.resolve_after_request()
        if after_request:
            return await after_request(response)
        return response


route = HTTPRouteHandler


class get(HTTPRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHandler] = None,
        after_response: Optional[AfterResponseHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHandler] = None,
        cache: Union[bool, int] = False,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        media_type: Union[MediaType, str] = MediaType.JSON,
        middleware: Optional[List[Middleware]] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[Type[Response]] = None,
        response_cookies: Optional[List[Cookie]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
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
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        GET Route Decorator. Use this decorator to decorate an HTTP handler for GET requests.

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
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string/[Provider][starlite.provide.Provide] dictionary that maps dependency providers.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            opt: A string key dictionary of arbitrary values that can be accessed [Guards][starlite.types.Guard].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            status_code: An http status code for the response. Defaults to '200'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the
                OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the
                wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI
                documentation. This list should describe all exceptions raised within the route handler's
                function/method. The Starlite ValidationException will be added automatically for the schema if
                any validation is involved.
            response_description: Text used for the route's response schema description section.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
        """
        super().__init__(
            after_request=after_request,
            after_response=after_response,
            background=background,
            before_request=before_request,
            cache=cache,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            dependencies=dependencies,
            deprecated=deprecated,
            description=description,
            exception_handlers=exception_handlers,
            guards=guards,
            http_method=HttpMethod.GET,
            include_in_schema=include_in_schema,
            media_type=media_type,
            middleware=middleware,
            operation_id=operation_id,
            opt=opt,
            path=path,
            raises=raises,
            response_class=response_class,
            response_description=response_description,
            response_cookies=response_cookies,
            response_headers=response_headers,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
        )


class post(HTTPRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHandler] = None,
        after_response: Optional[AfterResponseHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHandler] = None,
        cache: Union[bool, int] = False,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        media_type: Union[MediaType, str] = MediaType.JSON,
        middleware: Optional[List[Middleware]] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[Type[Response]] = None,
        response_cookies: Optional[List[Cookie]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
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
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        POST Route Decorator. Use this decorator to decorate an HTTP handler for POST requests.

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
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string/[Provider][starlite.provide.Provide] dictionary that maps dependency providers.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            opt: A string key dictionary of arbitrary values that can be accessed [Guards][starlite.types.Guard].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            status_code: An http status code for the response. Defaults to '201' for 'POST'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the
                OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the
                wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI
                documentation. This list should describe all exceptions raised within the route handler's
                function/method. The Starlite ValidationException will be added automatically for the schema if
                any validation is involved.
            response_description: Text used for the route's response schema description section.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
        """
        super().__init__(
            after_request=after_request,
            after_response=after_response,
            background=background,
            before_request=before_request,
            cache=cache,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            dependencies=dependencies,
            deprecated=deprecated,
            description=description,
            exception_handlers=exception_handlers,
            guards=guards,
            http_method=HttpMethod.POST,
            include_in_schema=include_in_schema,
            media_type=media_type,
            middleware=middleware,
            operation_id=operation_id,
            opt=opt,
            path=path,
            raises=raises,
            response_class=response_class,
            response_description=response_description,
            response_cookies=response_cookies,
            response_headers=response_headers,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
        )


class put(HTTPRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHandler] = None,
        after_response: Optional[AfterResponseHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHandler] = None,
        cache: Union[bool, int] = False,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        media_type: Union[MediaType, str] = MediaType.JSON,
        middleware: Optional[List[Middleware]] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[Type[Response]] = None,
        response_cookies: Optional[List[Cookie]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
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
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        PUT Route Decorator. Use this decorator to decorate an HTTP handler for PUT requests.

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
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string/[Provider][starlite.provide.Provide] dictionary that maps dependency providers.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            opt: A string key dictionary of arbitrary values that can be accessed [Guards][starlite.types.Guard].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            status_code: An http status code for the response. Defaults to '200'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the
                OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the
                wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI
                documentation. This list should describe all exceptions raised within the route handler's
                function/method. The Starlite ValidationException will be added automatically for the schema if
                any validation is involved.
            response_description: Text used for the route's response schema description section.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
        """
        super().__init__(
            after_request=after_request,
            after_response=after_response,
            background=background,
            before_request=before_request,
            cache=cache,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            dependencies=dependencies,
            deprecated=deprecated,
            description=description,
            exception_handlers=exception_handlers,
            guards=guards,
            http_method=HttpMethod.PUT,
            include_in_schema=include_in_schema,
            media_type=media_type,
            middleware=middleware,
            operation_id=operation_id,
            opt=opt,
            path=path,
            raises=raises,
            response_class=response_class,
            response_description=response_description,
            response_cookies=response_cookies,
            response_headers=response_headers,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
        )


class patch(HTTPRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHandler] = None,
        after_response: Optional[AfterResponseHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHandler] = None,
        cache: Union[bool, int] = False,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        media_type: Union[MediaType, str] = MediaType.JSON,
        middleware: Optional[List[Middleware]] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[Type[Response]] = None,
        response_cookies: Optional[List[Cookie]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
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
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        PATCH Route Decorator. Use this decorator to decorate an HTTP handler for PATCH requests.

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
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string/[Provider][starlite.provide.Provide] dictionary that maps dependency providers.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            opt: A string key dictionary of arbitrary values that can be accessed [Guards][starlite.types.Guard].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            status_code: An http status code for the response. Defaults to '200'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the
                OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the
                wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI
                documentation. This list should describe all exceptions raised within the route handler's
                function/method. The Starlite ValidationException will be added automatically for the schema if
                any validation is involved.
            response_description: Text used for the route's response schema description section.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
        """
        super().__init__(
            after_request=after_request,
            after_response=after_response,
            background=background,
            before_request=before_request,
            cache=cache,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            dependencies=dependencies,
            deprecated=deprecated,
            description=description,
            exception_handlers=exception_handlers,
            guards=guards,
            http_method=HttpMethod.PATCH,
            include_in_schema=include_in_schema,
            media_type=media_type,
            middleware=middleware,
            operation_id=operation_id,
            opt=opt,
            path=path,
            raises=raises,
            response_class=response_class,
            response_description=response_description,
            response_cookies=response_cookies,
            response_headers=response_headers,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
        )


class delete(HTTPRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHandler] = None,
        after_response: Optional[AfterResponseHandler] = None,
        background: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
        before_request: Optional[BeforeRequestHandler] = None,
        cache: Union[bool, int] = False,
        cache_key_builder: Optional[CacheKeyBuilder] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        media_type: Union[MediaType, str] = MediaType.JSON,
        middleware: Optional[List[Middleware]] = None,
        opt: Optional[Dict[str, Any]] = None,
        response_class: Optional[Type[Response]] = None,
        response_cookies: Optional[List[Cookie]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
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
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        DELETE Route Decorator. Use this decorator to decorate an HTTP handler for DELETE requests.

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
            cache_key_builder: A [cache-key builder function][starlite.types.CacheKeyBuilder]. Allows for customization
                of the cache key if caching is configured on the application level.
            dependencies: A string/[Provider][starlite.provide.Provide] dictionary that maps dependency providers.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            media_type: A member of the [MediaType][starlite.enums.MediaType] enum or a string with a
                valid IANA Media-Type.
            middleware: A list of [Middleware][starlite.types.Middleware].
            opt: A string key dictionary of arbitrary values that can be accessed [Guards][starlite.types.Guard].
            response_class: A custom subclass of [starlite.response.Response] to be used as route handler's
                default response.
            response_cookies: A list of [Cookie](starlite.datastructures.Cookie] instances.
            response_headers: A string keyed dictionary mapping [ResponseHeader][starlite.datastructures.ResponseHeader]
                instances.
            status_code: An http status code for the response. Defaults to '204'.
            sync_to_thread: A boolean dictating whether the handler function will be executed in a worker thread or the
                main event loop. This has an effect only for sync handler functions. See using sync handler functions.
            content_encoding: A string describing the encoding of the content, e.g. "base64".
            content_media_type: A string designating the media-type of the content, e.g. "image/png".
            deprecated:  A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema.
            description: Text used for the route's schema description section.
            include_in_schema: A boolean flag dictating whether  the route handler should be documented in the
                OpenAPI schema.
            operation_id: An identifier used for the route's schema operationId. Defaults to the __name__ of the
                wrapped function.
            raises:  A list of exception classes extending from starlite.HttpException that is used for the OpenAPI
                documentation. This list should describe all exceptions raised within the route handler's
                function/method. The Starlite ValidationException will be added automatically for the schema if
                any validation is involved.
            response_description: Text used for the route's response schema description section.
            summary: Text used for the route's schema summary section.
            tags: A list of string tags that will be appended to the OpenAPI schema.
        """
        super().__init__(
            after_request=after_request,
            after_response=after_response,
            background=background,
            before_request=before_request,
            cache=cache,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            dependencies=dependencies,
            deprecated=deprecated,
            description=description,
            exception_handlers=exception_handlers,
            guards=guards,
            http_method=HttpMethod.DELETE,
            include_in_schema=include_in_schema,
            media_type=media_type,
            middleware=middleware,
            operation_id=operation_id,
            opt=opt,
            path=path,
            raises=raises,
            response_class=response_class,
            response_description=response_description,
            response_cookies=response_cookies,
            response_headers=response_headers,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
        )
