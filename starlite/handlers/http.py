# pylint: disable=too-many-instance-attributes, too-many-arguments
from __future__ import annotations

from contextlib import suppress
from enum import Enum
from inspect import Signature, isawaitable, isclass, ismethod
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    Union,
    cast,
)

from anyio.to_thread import run_sync
from pydantic import validate_arguments
from pydantic.typing import AnyCallable
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
from starlite.plugins import PluginProtocol, get_plugin_for_value
from starlite.provide import Provide
from starlite.response import Response, TemplateResponse
from starlite.types import (
    AfterRequestHandler,
    BeforeRequestHandler,
    CacheKeyBuilder,
    ExceptionHandler,
    Guard,
    Method,
    Middleware,
    ResponseHeader,
)
from starlite.utils import is_async_callable

if TYPE_CHECKING:  # pragma: no cover
    from starlite.app import Starlite
    from starlite.controller import Controller
    from starlite.router import Router


class HTTPRouteHandler(BaseRouteHandler):
    __slots__ = (
        "after_request",
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
        path: str | None | list[str] | None = None,
        http_method: HttpMethod | Method | list[HttpMethod | Method] = None,  # type: ignore
        after_request: AfterRequestHandler | None = None,
        background_tasks: BackgroundTask | BackgroundTasks | None = None,
        before_request: BeforeRequestHandler | None = None,
        dependencies: dict[str, Provide] | None = None,
        guards: list[Guard] | None = None,
        media_type: MediaType | str = MediaType.JSON,
        opt: dict[str, Any] | None = None,
        response_class: type[Response] | None = None,
        response_headers: dict[str, ResponseHeader] | None = None,
        status_code: int | None = None,
        cache: bool | int = False,
        cache_key_builder: CacheKeyBuilder | None = None,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        middleware: list[Middleware] | None = None,
        # sync only
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: str | None = None,
        content_media_type: str | None = None,
        deprecated: bool = False,
        description: str | None = None,
        include_in_schema: bool = True,
        operation_id: str | None = None,
        raises: list[type[HTTPException]] | None = None,
        response_description: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ):
        if not http_method:
            raise ImproperlyConfiguredException("An http_method kwarg is required")
        if isinstance(http_method, list):
            self.http_method: list[str] | str = [v.upper() for v in http_method]
            if len(http_method) == 1:
                self.http_method = http_method[0]
        else:
            self.http_method = http_method.value if isinstance(http_method, HttpMethod) else http_method
        if status_code:
            self.status_code = status_code
        elif isinstance(self.http_method, list):
            self.status_code = HTTP_200_OK
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
        self.before_request = before_request
        self.background_tasks = background_tasks
        self.media_type = media_type
        self.response_class = response_class
        self.response_headers = response_headers
        self.cache = cache
        self.cache_key_builder = cache_key_builder
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
        self.resolved_headers: dict[str, ResponseHeader] | type[BaseRouteHandler.empty] = BaseRouteHandler.empty
        self.resolved_response_class: type[Response] | type[BaseRouteHandler.empty] = BaseRouteHandler.empty
        self.resolved_after_request: (
            BeforeRequestHandler | None | type[BaseRouteHandler.empty]
        ) = BaseRouteHandler.empty
        self.resolved_before_request: (
            BeforeRequestHandler | None | type[BaseRouteHandler.empty]
        ) = BaseRouteHandler.empty

    def __call__(self, fn: AnyCallable) -> HTTPRouteHandler:
        """
        Replaces a function with itself
        """
        self.fn = fn
        self.validate_handler_function()
        return self

    def ownership_layers(self) -> Generator[HTTPRouteHandler | Controller | Router, None, None]:
        """
        Returns all the handler and then all owners up to the app level

        handler -> ... -> App
        """
        return cast(
            Generator[Union["HTTPRouteHandler", "Controller", "Router"], None, None], super().ownership_layers()
        )

    def resolve_response_class(self) -> type[Response]:
        """
        Returns the closest custom Response class in the owner graph or the default Response class.

        This method is memoized so the computation occurs only once.
        """
        if self.resolved_response_class is BaseRouteHandler.empty:
            self.resolved_response_class = Response
            for layer in self.ownership_layers():
                if layer.response_class is not None:
                    self.resolved_response_class = layer.response_class
                    break
        return cast(Type[Response], self.resolved_response_class)

    def resolve_response_headers(self) -> dict[str, ResponseHeader]:
        """
        Returns all header parameters in the scope of the handler function

        This method is memoized so the computation occurs only once.
        """
        if self.resolved_headers is BaseRouteHandler.empty:
            headers: dict[str, ResponseHeader] = {}
            for layer in reversed(list(self.ownership_layers())):
                headers = {**headers, **(layer.response_headers or {})}
            self.resolved_headers = headers
        return cast(Dict[str, ResponseHeader], self.resolved_headers)

    def resolve_before_request(self) -> BeforeRequestHandler | None:
        """
        Resolves the before_handler handler by starting from the route handler and moving up.

        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once
        """
        if self.resolved_before_request is BaseRouteHandler.empty:
            for layer in self.ownership_layers():
                if layer.before_request:
                    self.resolved_before_request = layer.before_request
                    break
            if self.resolved_before_request is BaseRouteHandler.empty:
                self.resolved_before_request = None
            elif ismethod(self.resolved_before_request):
                # python automatically binds class variables, which we do not want in this case.
                self.resolved_before_request = self.resolved_before_request.__func__
        return self.resolved_before_request

    def resolve_after_request(self) -> AfterRequestHandler | None:
        """
        Resolves the after_request handler by starting from the route handler and moving up.

        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once
        """
        if self.resolved_after_request is BaseRouteHandler.empty:
            for layer in self.ownership_layers():
                if layer.after_request:
                    self.resolved_after_request = layer.after_request  # type: ignore
                    break
            if self.resolved_after_request is BaseRouteHandler.empty:
                self.resolved_after_request = None
            elif ismethod(self.resolved_after_request):
                # python automatically binds class variables, which we do not want in this case.
                self.resolved_after_request = self.resolved_after_request.__func__
        return cast(Optional[AfterRequestHandler], self.resolved_after_request)

    @property
    def http_methods(self) -> list[Method]:
        """
        Returns a list of the RouteHandler's HttpMethod members
        """
        return cast(List[Method], self.http_method if isinstance(self.http_method, list) else [self.http_method])

    def validate_handler_function(self) -> None:
        """
        Validates the route handler function once it is set by inspecting its return annotations
        """
        super().validate_handler_function()
        signature = Signature.from_callable(cast(AnyCallable, self.fn))
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
        data: StarletteResponse | StarliteType,
        media_type: MediaType | str,
        app: Starlite,
    ) -> StarletteResponse:
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
        return cast(StarletteResponse, data)

    @staticmethod
    async def _process_after_request_hook(
        response: StarletteResponse,
        after_request: AfterRequestHandler | None = None,
    ) -> StarletteResponse:
        if after_request:
            if is_async_callable(after_request):
                return await after_request(response)  # type: ignore[no-any-return,misc,arg-type]
            return await run_sync(after_request, response)  # type: ignore[arg-type]
        return response

    async def to_response(self, data: Any, app: "Starlite", plugins: list[PluginProtocol]) -> StarletteResponse:
        """
        Given a data kwarg, determine its type and return the appropriate response
        """
        if isawaitable(data):
            data = await data
        after_request = self.resolve_after_request()
        media_type = self.media_type.value if isinstance(self.media_type, Enum) else self.media_type
        headers = {k: v.value for k, v in self.resolve_response_headers().items()}
        response: StarletteResponse
        if isinstance(data, (StarletteResponse, StarliteType)):
            response = self._get_response_from_data(headers=headers, data=data, media_type=media_type, app=app)
        else:
            plugin = get_plugin_for_value(value=data, plugins=plugins)
            if plugin:
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
        return await self._process_after_request_hook(response, after_request)


route = HTTPRouteHandler


class get(HTTPRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: str | None | list[str] | None = None,
        dependencies: dict[str, Provide] | None = None,
        guards: list[Guard] | None = None,
        opt: dict[str, Any] | None = None,
        after_request: AfterRequestHandler | None = None,
        before_request: BeforeRequestHandler | None = None,
        media_type: MediaType | str = MediaType.JSON,
        response_class: type[Response] | None = None,
        response_headers: dict[str, ResponseHeader] | None = None,
        status_code: int | None = None,
        cache: bool | int = False,
        cache_key_builder: CacheKeyBuilder | None = None,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        middleware: list[Middleware] | None = None,
        # sync only
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: str | None = None,
        content_media_type: str | None = None,
        deprecated: bool = False,
        description: str | None = None,
        include_in_schema: bool = True,
        operation_id: str | None = None,
        raises: list[type[HTTPException]] | None = None,
        response_description: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ):
        super().__init__(
            http_method=HttpMethod.GET,
            path=path,
            dependencies=dependencies,
            guards=guards,
            opt=opt,
            after_request=after_request,
            before_request=before_request,
            media_type=media_type,
            response_class=response_class,
            response_headers=response_headers,
            status_code=status_code,
            cache=cache,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            deprecated=deprecated,
            description=description,
            include_in_schema=include_in_schema,
            operation_id=operation_id,
            raises=raises,
            response_description=response_description,
            summary=summary,
            tags=tags,
            sync_to_thread=sync_to_thread,
            exception_handlers=exception_handlers,
            middleware=middleware,
        )


class post(HTTPRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: str | None | list[str] | None = None,
        dependencies: dict[str, Provide] | None = None,
        guards: list[Guard] | None = None,
        opt: dict[str, Any] | None = None,
        after_request: AfterRequestHandler | None = None,
        before_request: BeforeRequestHandler | None = None,
        media_type: MediaType | str = MediaType.JSON,
        response_class: type[Response] | None = None,
        response_headers: dict[str, ResponseHeader] | None = None,
        status_code: int | None = None,
        cache: bool | int = False,
        cache_key_builder: CacheKeyBuilder | None = None,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        middleware: list[Middleware] | None = None,
        # sync only
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: str | None = None,
        content_media_type: str | None = None,
        deprecated: bool = False,
        description: str | None = None,
        include_in_schema: bool = True,
        operation_id: str | None = None,
        raises: list[type[HTTPException]] | None = None,
        response_description: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ):
        super().__init__(
            http_method=HttpMethod.POST,
            path=path,
            dependencies=dependencies,
            guards=guards,
            opt=opt,
            after_request=after_request,
            before_request=before_request,
            media_type=media_type,
            response_class=response_class,
            response_headers=response_headers,
            status_code=status_code,
            cache=cache,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            deprecated=deprecated,
            description=description,
            include_in_schema=include_in_schema,
            operation_id=operation_id,
            raises=raises,
            response_description=response_description,
            summary=summary,
            tags=tags,
            sync_to_thread=sync_to_thread,
            exception_handlers=exception_handlers,
            middleware=middleware,
        )


class put(HTTPRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: str | None | list[str] | None = None,
        dependencies: dict[str, Provide] | None = None,
        guards: list[Guard] | None = None,
        opt: dict[str, Any] | None = None,
        after_request: AfterRequestHandler | None = None,
        before_request: BeforeRequestHandler | None = None,
        media_type: MediaType | str = MediaType.JSON,
        response_class: type[Response] | None = None,
        response_headers: dict[str, ResponseHeader] | None = None,
        status_code: int | None = None,
        cache: bool | int = False,
        cache_key_builder: CacheKeyBuilder | None = None,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        middleware: list[Middleware] | None = None,
        # sync only
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: str | None = None,
        content_media_type: str | None = None,
        deprecated: bool = False,
        description: str | None = None,
        include_in_schema: bool = True,
        operation_id: str | None = None,
        raises: list[type[HTTPException]] | None = None,
        response_description: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ):
        super().__init__(
            http_method=HttpMethod.PUT,
            path=path,
            dependencies=dependencies,
            guards=guards,
            opt=opt,
            after_request=after_request,
            before_request=before_request,
            media_type=media_type,
            response_class=response_class,
            response_headers=response_headers,
            status_code=status_code,
            cache=cache,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            deprecated=deprecated,
            description=description,
            include_in_schema=include_in_schema,
            operation_id=operation_id,
            raises=raises,
            response_description=response_description,
            summary=summary,
            tags=tags,
            sync_to_thread=sync_to_thread,
            exception_handlers=exception_handlers,
            middleware=middleware,
        )


class patch(HTTPRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: str | None | list[str] | None = None,
        dependencies: dict[str, Provide] | None = None,
        guards: list[Guard] | None = None,
        opt: dict[str, Any] | None = None,
        after_request: AfterRequestHandler | None = None,
        before_request: BeforeRequestHandler | None = None,
        media_type: MediaType | str = MediaType.JSON,
        response_class: type[Response] | None = None,
        response_headers: dict[str, ResponseHeader] | None = None,
        status_code: int | None = None,
        cache: bool | int = False,
        cache_key_builder: CacheKeyBuilder | None = None,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        middleware: list[Middleware] | None = None,
        # sync only
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: str | None = None,
        content_media_type: str | None = None,
        deprecated: bool = False,
        description: str | None = None,
        include_in_schema: bool = True,
        operation_id: str | None = None,
        raises: list[type[HTTPException]] | None = None,
        response_description: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ):
        super().__init__(
            http_method=HttpMethod.PATCH,
            path=path,
            dependencies=dependencies,
            guards=guards,
            opt=opt,
            after_request=after_request,
            before_request=before_request,
            media_type=media_type,
            response_class=response_class,
            response_headers=response_headers,
            status_code=status_code,
            cache=cache,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            deprecated=deprecated,
            description=description,
            include_in_schema=include_in_schema,
            operation_id=operation_id,
            raises=raises,
            response_description=response_description,
            summary=summary,
            tags=tags,
            sync_to_thread=sync_to_thread,
            exception_handlers=exception_handlers,
            middleware=middleware,
        )


class delete(HTTPRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: str | None | list[str] | None = None,
        dependencies: dict[str, Provide] | None = None,
        guards: list[Guard] | None = None,
        opt: dict[str, Any] | None = None,
        after_request: AfterRequestHandler | None = None,
        before_request: BeforeRequestHandler | None = None,
        media_type: MediaType | str = MediaType.JSON,
        response_class: type[Response] | None = None,
        response_headers: dict[str, ResponseHeader] | None = None,
        status_code: int | None = None,
        cache: bool | int = False,
        cache_key_builder: CacheKeyBuilder | None = None,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        middleware: list[Middleware] | None = None,
        # sync only
        sync_to_thread: bool = False,
        # OpenAPI related attributes
        content_encoding: str | None = None,
        content_media_type: str | None = None,
        deprecated: bool = False,
        description: str | None = None,
        include_in_schema: bool = True,
        operation_id: str | None = None,
        raises: list[type[HTTPException]] | None = None,
        response_description: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ):
        super().__init__(
            http_method=HttpMethod.DELETE,
            path=path,
            dependencies=dependencies,
            guards=guards,
            opt=opt,
            after_request=after_request,
            before_request=before_request,
            media_type=media_type,
            response_class=response_class,
            response_headers=response_headers,
            status_code=status_code,
            cache=cache,
            cache_key_builder=cache_key_builder,
            content_encoding=content_encoding,
            content_media_type=content_media_type,
            deprecated=deprecated,
            description=description,
            include_in_schema=include_in_schema,
            operation_id=operation_id,
            raises=raises,
            response_description=response_description,
            summary=summary,
            tags=tags,
            sync_to_thread=sync_to_thread,
            exception_handlers=exception_handlers,
            middleware=middleware,
        )
