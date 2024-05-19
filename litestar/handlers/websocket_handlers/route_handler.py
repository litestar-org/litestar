from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Mapping

from litestar.connection import WebSocket
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers import BaseRouteHandler
from litestar.types import AsyncAnyCallable, Empty
from litestar.types.builtin_types import NoneType
from litestar.utils.predicates import is_async_callable

if TYPE_CHECKING:
    from litestar._kwargs import KwargsModel
    from litestar._kwargs.cleanup import DependencyCleanupGroup
    from litestar.app import Litestar
    from litestar.routes import BaseRoute
    from litestar.types import Dependencies, EmptyType, ExceptionHandler, Guard, Middleware


class WebsocketRouteHandler(BaseRouteHandler):
    """Websocket route handler decorator.

    Use this decorator to decorate websocket handler functions.
    """

    __slots__ = ("websocket_class", "_kwargs_model")

    def __init__(
        self,
        path: str | list[str] | None = None,
        *,
        fn: AsyncAnyCallable,
        dependencies: Dependencies | None = None,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        guards: list[Guard] | None = None,
        middleware: list[Middleware] | None = None,
        name: str | None = None,
        opt: dict[str, Any] | None = None,
        signature_namespace: Mapping[str, Any] | None = None,
        websocket_class: type[WebSocket] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ``WebsocketRouteHandler``

        Args:
            path: A path fragment for the route handler function or a sequence of path fragments. If not given defaults
                to ``/``
            fn: The handler function

                .. versionadded:: 3.0
            dependencies: A string keyed mapping of dependency :class:`Provider <.di.Provide>` instances.
            exception_handlers: A mapping of status codes and/or exception types to handler functions.
            guards: A sequence of :class:`Guard <.types.Guard>` callables.
            middleware: A sequence of :class:`Middleware <.types.Middleware>`.
            name: A string identifying the route handler.
            opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
                wherever you have access to :class:`Request <.connection.Request>` or
                :class:`ASGI Scope <.types.Scope>`.
            signature_namespace: A mapping of names to types for use in forward reference resolution during signature modelling.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
            websocket_class: A custom subclass of :class:`WebSocket <.connection.WebSocket>` to be used as route handler's
                default websocket class.
        """
        self.websocket_class = websocket_class
        self._kwargs_model: KwargsModel | EmptyType = Empty

        super().__init__(
            fn=fn,
            path=path,
            dependencies=dependencies,
            exception_handlers=exception_handlers,
            guards=guards,
            middleware=middleware,
            name=name,
            opt=opt,
            signature_namespace=signature_namespace,
            **kwargs,
        )

    def resolve_websocket_class(self) -> type[WebSocket]:
        """Return the closest custom WebSocket class in the owner graph or the default Websocket class.

        This method is memoized so the computation occurs only once.

        Returns:
            The default :class:`WebSocket <.connection.WebSocket>` class for the route handler.
        """
        return next(
            (layer.websocket_class for layer in reversed(self.ownership_layers) if layer.websocket_class is not None),
            WebSocket,
        )

    def _validate_handler_function(self) -> None:
        """Validate the route handler function once it's set by inspecting its return annotations."""
        super()._validate_handler_function()

        if not self.parsed_fn_signature.return_type.is_subclass_of(NoneType):
            raise ImproperlyConfiguredException("Websocket handler functions should return 'None'")

        if "socket" not in self.parsed_fn_signature.parameters:
            raise ImproperlyConfiguredException("Websocket handlers must set a 'socket' kwarg")

        for param in ("request", "body", "data"):
            if param in self.parsed_fn_signature.parameters:
                raise ImproperlyConfiguredException(f"The {param} kwarg is not supported with websocket handlers")

        if not is_async_callable(self.fn):
            raise ImproperlyConfiguredException("Functions decorated with 'websocket' must be async functions")

    def on_registration(self, app: Litestar, route: BaseRoute) -> None:
        super().on_registration(app=app, route=route)
        self._kwargs_model = self._create_kwargs_model(path_parameters=route.path_parameters)

    async def handle(self, connection: WebSocket[Any, Any, Any]) -> None:
        """ASGI app that creates a WebSocket from the passed in args, and then awaits the handler function.

        Args:
            connection: WebSocket connection

        Returns:
            None
        """

        handler_parameter_model = self._kwargs_model
        if handler_parameter_model is Empty:
            raise ImproperlyConfiguredException("handler parameter model not defined")

        if self.resolve_guards():
            await self.authorize_connection(connection=connection)

        parsed_kwargs: dict[str, Any] = {}
        cleanup_group: DependencyCleanupGroup | None = None

        if handler_parameter_model.has_kwargs and self.signature_model:
            parsed_kwargs = handler_parameter_model.to_kwargs(connection=connection)

            if handler_parameter_model.dependency_batches:
                cleanup_group = await handler_parameter_model.resolve_dependencies(connection, parsed_kwargs)

            parsed_kwargs = self.signature_model.parse_values_from_connection_kwargs(
                connection=connection, **parsed_kwargs
            )

        if cleanup_group:
            async with cleanup_group:
                await self.fn(**parsed_kwargs)
            await cleanup_group.cleanup()
        else:
            await self.fn(**parsed_kwargs)


def websocket(
    path: str | list[str] | None = None,
    *,
    dependencies: Dependencies | None = None,
    exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
    guards: list[Guard] | None = None,
    middleware: list[Middleware] | None = None,
    name: str | None = None,
    opt: dict[str, Any] | None = None,
    signature_namespace: Mapping[str, Any] | None = None,
    websocket_class: type[WebSocket] | None = None,
    **kwargs: Any,
) -> Callable[[AsyncAnyCallable], WebsocketRouteHandler]:
    def decorator(fn: AsyncAnyCallable) -> WebsocketRouteHandler:
        return WebsocketRouteHandler(
            path=path,
            fn=fn,
            dependencies=dependencies,
            exception_handlers=exception_handlers,
            guards=guards,
            middleware=middleware,
            name=name,
            opt=opt,
            signature_namespace=signature_namespace,
            websocket_class=websocket_class,
            **kwargs,
        )

    return decorator
