# pylint: disable=too-many-instance-attributes
from contextlib import suppress
from enum import Enum
from inspect import Signature, isawaitable, isclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union, cast

from pydantic import validate_arguments
from starlette.background import BackgroundTask, BackgroundTasks
from starlette.responses import FileResponse, RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from starlite.constants import REDIRECT_STATUS_CODES
from starlite.datastructures import File, Redirect, StarliteType, Stream, Template
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
    ExceptionHandler,
    Guard,
    Method,
    Middleware,
    ResponseHeader,
)
from starlite.utils import is_async_callable

if TYPE_CHECKING:
    from pydantic.typing import AnyCallable

    from starlite.app import Starlite


class HTTPRouteHandler(BaseRouteHandler["HTTPRouteHandler"]):
    __slots__ = (
        "after_request",
        "after_response",
        "background_tasks",
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
        "resolved_after_request",
        "resolved_before_request",
        "resolved_after_response",
        "resolved_headers",
        "resolved_response_class",
        "response_class",
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
        background_tasks: Optional[Union[BackgroundTask, BackgroundTasks]] = None,
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
        self.background_tasks = background_tasks
        self.before_request = before_request
        self.cache = cache
        self.cache_key_builder = cache_key_builder
        self.media_type = media_type
        self.response_class = response_class
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
        # memoized attributes, defaulted to BaseRouteHandler.empty
        self.resolved_after_request: Union[
            Optional[AfterRequestHook], Type[BaseRouteHandler.empty]
        ] = BaseRouteHandler.empty
        self.resolved_after_response: Union[
            Optional[AfterResponseHook], Type[BaseRouteHandler.empty]
        ] = BaseRouteHandler.empty
        self.resolved_before_request: Union[
            Optional[BeforeRequestHook], Type[BaseRouteHandler.empty]
        ] = BaseRouteHandler.empty
        self.resolved_headers: Union[Dict[str, ResponseHeader], Type[BaseRouteHandler.empty]] = BaseRouteHandler.empty
        self.resolved_response_class: Union[Type[Response], Type[BaseRouteHandler.empty]] = BaseRouteHandler.empty

    def __call__(self, fn: "AnyCallable") -> "HTTPRouteHandler":
        """
        Replaces a function with itself
        """
        self.fn = fn
        self.validate_handler_function()
        return self

    def resolve_response_class(self) -> Type[Response]:
        """
        Returns the closest custom Response class in the owner graph or the default Response class.

        This method is memoized so the computation occurs only once.
        """
        if self.resolved_response_class is BaseRouteHandler.empty:
            self.resolved_response_class = Response
            for layer in self.ownership_layers:
                if layer.response_class is not None:
                    self.resolved_response_class = layer.response_class
        return cast("Type[Response]", self.resolved_response_class)

    def resolve_response_headers(self) -> Dict[str, "ResponseHeader"]:
        """
        Returns all header parameters in the scope of the handler function

        This method is memoized so the computation occurs only once.
        """
        if self.resolved_headers is BaseRouteHandler.empty:
            self.resolved_headers = {}
            for layer in self.ownership_layers:
                self.resolved_headers.update(layer.response_headers or {})
        return cast("Dict[str, ResponseHeader]", self.resolved_headers)

    def resolve_before_request(self) -> Optional["BeforeRequestHook"]:
        """
        Resolves the before_handler handler by starting from the route handler and moving up.

        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once
        """
        if self.resolved_before_request is BaseRouteHandler.empty:
            self.resolved_before_request = BeforeRequestHook.resolve_for_handler(self, "before_request")
        return cast("Optional[BeforeRequestHook]", self.resolved_before_request)

    def resolve_after_request(self) -> Optional["AfterRequestHook"]:
        """
        Resolves the after_request handler by starting from the route handler and moving up.

        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once
        """
        if self.resolved_after_request is BaseRouteHandler.empty:
            self.resolved_after_request = AfterRequestHook.resolve_for_handler(self, "after_request")
        return cast("Optional[AfterRequestHook]", self.resolved_after_request)

    def resolve_after_response(self) -> Optional["AfterResponseHook"]:
        """
        Resolves the after_response handler by starting from the route handler and moving up.

        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once
        """
        if self.resolved_after_response is BaseRouteHandler.empty:
            self.resolved_after_response = AfterResponseHook.resolve_for_handler(self, "after_response")
        return cast("Optional[AfterResponseHook]", self.resolved_after_response)

    @property
    def http_methods(self) -> List["Method"]:
        """
        Returns a list of the RouteHandler's HttpMethod members
        """
        return cast("List[Method]", self.http_method if isinstance(self.http_method, list) else [self.http_method])

    def validate_handler_function(self) -> None:
        """
        Validates the route handler function once it is set by inspecting its return annotations
        """
        super().validate_handler_function()
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

    def _get_response_from_data(
        self,
        headers: dict,
        data: Union[StarletteResponse, StarliteType],
        media_type: Union[MediaType, str],
        app: "Starlite",
    ) -> StarletteResponse:
        """
        Determines the correct response type to return given data
        """
        if isinstance(data, Redirect):
            return RedirectResponse(headers=headers, status_code=self.status_code, url=data.path)
        if isinstance(data, File):
            return FileResponse(media_type=media_type, headers=headers, **data.dict())
        if isinstance(data, Stream):
            return StreamingResponse(
                content=data.iterator, status_code=self.status_code, media_type=media_type, headers=headers
            )
        if isinstance(data, Template):
            if not app.template_engine:
                raise ImproperlyConfiguredException("Template engine is not configured")
            return TemplateResponse(
                context=data.context,
                template_name=data.name,
                template_engine=app.template_engine,
                status_code=self.status_code,
                headers=headers,
            )
        return cast("StarletteResponse", data)

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

    async def to_response(self, data: Any, app: "Starlite", plugins: List[PluginProtocol]) -> StarletteResponse:
        """
        Given a data kwarg, determine its type and return the appropriate response
        """
        if isawaitable(data):
            data = await data
        media_type = self.media_type.value if isinstance(self.media_type, Enum) else self.media_type
        headers = {k: v.value for k, v in self.resolve_response_headers().items()}
        response: StarletteResponse
        if isinstance(data, (StarletteResponse, StarliteType)):
            response = self._get_response_from_data(headers=headers, data=data, media_type=media_type, app=app)
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
                headers=headers,
                status_code=self.status_code,
                content=data,
                media_type=media_type,
                background=self.background_tasks,
            )
        return await self._process_after_request_hook(response)


route = HTTPRouteHandler


class get(HTTPRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        after_request: Optional[AfterRequestHandler] = None,
        after_response: Optional[AfterResponseHandler] = None,
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
        super().__init__(
            after_request=after_request,
            after_response=after_response,
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
        super().__init__(
            after_request=after_request,
            after_response=after_response,
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
        super().__init__(
            after_request=after_request,
            after_response=after_response,
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
        super().__init__(
            after_request=after_request,
            after_response=after_response,
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
        super().__init__(
            after_request=after_request,
            after_response=after_response,
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
            response_headers=response_headers,
            status_code=status_code,
            summary=summary,
            sync_to_thread=sync_to_thread,
            tags=tags,
        )
