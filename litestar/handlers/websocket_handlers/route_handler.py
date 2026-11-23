from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar._request_parameters.validation import create_request_param_validaton_fn
from litestar.connection import WebSocket
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers import BaseRouteHandler
from litestar.types.builtin_types import NoneType
from litestar.utils import deprecated
from litestar.utils.predicates import is_async_callable

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from litestar import Litestar, Router
    from litestar.routes import BaseRoute
    from litestar.types import AsyncAnyCallable, Dependencies, ExceptionHandler, Guard, Middleware, ParametersMap


class WebsocketRouteHandler(BaseRouteHandler):
    __slots__ = ("_websocket_class",)

    def __init__(
        self,
        path: str | list[str] | None = None,
        *,
        fn: AsyncAnyCallable,
        dependencies: Dependencies | None = None,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        guards: Sequence[Guard] | None = None,
        middleware: Sequence[Middleware] | None = None,
        name: str | None = None,
        opt: dict[str, Any] | None = None,
        signature_namespace: Mapping[str, Any] | None = None,
        websocket_class: type[WebSocket] | None = None,
        parameters: ParametersMap | None = None,
        **kwargs: Any,
    ) -> None:
        """Route handler for WebSocket routes.

        Args:
            path: A path fragment for the route handler function or a sequence of path fragments. If not given defaults
                to ``/``
            fn: The handler function

                .. versionadded:: 3.0
            dependencies: A sequence of :class:`Provider <.di.Provider>` instances, or a mapping of names or types to providers, :class:`Provide <.di.Provide>` instances or callables.
            exception_handlers: A mapping of status codes and/or exception types to handler functions.
            guards: A sequence of :class:`Guard <.types.Guard>` callables.
            middleware: A sequence of :class:`Middleware <.types.Middleware>`.
            name: A string identifying the route handler.
            opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
                wherever you have access to :class:`Request <.connection.Request>` or
                :class:`ASGI Scope <.types.Scope>`.
            signature_namespace: A mapping of names to types for use in forward reference resolution during signature modelling.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            websocket_class: A custom subclass of :class:`WebSocket <.connection.WebSocket>` to be used as route handler's
                default websocket class.
            parameters: A mapping of :func:`Parameter <.params.ParameterKwarg>` definitions
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        self._websocket_class = websocket_class

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
            parameters=parameters,
            **kwargs,
        )

    def _get_merge_opts(self, others: tuple[Router, ...]) -> dict[str, Any]:
        merge_opts = super()._get_merge_opts(others)
        merge_opts["websocket_class"] = self._websocket_class or next(
            (o.websocket_class for o in others if o.websocket_class), None
        )

        return merge_opts

    @deprecated("3.0", removal_in="4.0", alternative=".websocket_class property")
    def resolve_websocket_class(self) -> type[WebSocket]:
        """Return the closest custom WebSocket class in the owner graph or the default Websocket class.

        This method is memoized so the computation occurs only once.

        Returns:
            The default :class:`WebSocket <.connection.WebSocket>` class for the route handler.
        """
        return self.websocket_class

    @property
    def websocket_class(self) -> type[WebSocket]:
        return self._websocket_class or WebSocket

    def _validate_handler_function(self) -> None:
        """Validate the route handler function once it's set by inspecting its return annotations."""
        super()._validate_handler_function()

        if not self.parsed_fn_signature.return_type.is_subclass_of(NoneType):
            raise ImproperlyConfiguredException(f"{self}: WebSocket handlers must return 'None'")

        if not is_async_callable(self.fn):
            raise ImproperlyConfiguredException(f"{self}: WebSocket handler functions must be asynchronous")

    def on_registration(self, route: BaseRoute, app: Litestar) -> None:
        super().on_registration(route=route, app=app)

        from litestar.di._route_handler import create_handler_injection_setup

        self._injection_setup = create_handler_injection_setup(
            self, app, connection_class=self.websocket_class, accepts_body=False
        )
        definitions = self._injection_setup.request_parameter_definitions
        self._validate_request_parameters = (
            create_request_param_validaton_fn(definitions.values(), dto_plan=None, type_decoders=self.type_decoders)
            if definitions
            else None
        )

    async def handle(self, connection: WebSocket[Any, Any, Any]) -> None:
        """ASGI app that creates a WebSocket from the passed in args, and then awaits the handler function.

        Args:
            connection: WebSocket connection

        Returns:
            None
        """

        if self.guards:
            await self.authorize_connection(connection=connection)

        setup = self._injection_setup
        validate = self._validate_request_parameters
        seeds: dict[Any, Any] = await validate(connection) if validate else {}
        for key in setup.connection_seed_keys:
            seeds[key] = connection
        kwargs = {name: seeds[key] for name, key in setup.fn_seed_parameters}
        async with self._create_di_handler_context(connection, seeds) as handler_context:
            kwargs.update(await handler_context.solve_arguments(setup.target, supplied=kwargs.keys()))
            await self.fn(**kwargs)


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
    handler_class: type[WebsocketRouteHandler] = WebsocketRouteHandler,
    **kwargs: Any,
) -> Callable[[AsyncAnyCallable], WebsocketRouteHandler]:
    """Create a :class:`WebsocketRouteHandler`.

    Args:
        path: A path fragment for the route handler function or a sequence of path fragments. If not given defaults
            to ``/``
        dependencies: A sequence of :class:`Provider <.di.Provider>` instances, or a mapping of names or types to providers, :class:`Provide <.di.Provide>` instances or callables.
        exception_handlers: A mapping of status codes and/or exception types to handler functions.
        guards: A sequence of :class:`Guard <.types.Guard>` callables.
        middleware: A sequence of :class:`Middleware <.types.Middleware>`.
        name: A string identifying the route handler.
        opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
            wherever you have access to :class:`Request <.connection.Request>` or
            :class:`ASGI Scope <.types.Scope>`.
        signature_namespace: A mapping of names to types for use in forward reference resolution during signature modelling.
        websocket_class: A custom subclass of :class:`WebSocket <.connection.WebSocket>` to be used as route handler's
            default websocket class.
        handler_class: Route handler class instantiated by the decorator
        **kwargs: Any additional kwarg - will be set in the opt dictionary.
    """

    def decorator(fn: AsyncAnyCallable) -> WebsocketRouteHandler:
        return handler_class(
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
