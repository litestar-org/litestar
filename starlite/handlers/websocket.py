from inspect import Signature
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union, cast

from pydantic import validate_arguments

from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers.base import BaseRouteHandler
from starlite.types import Dependencies, ExceptionHandler, Guard, Middleware
from starlite.utils import is_async_callable

if TYPE_CHECKING:
    from starlite.types import AnyCallable, AsyncAnyCallable


class WebsocketRouteHandler(BaseRouteHandler["WebsocketRouteHandler"]):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        dependencies: Optional[Dependencies] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        middleware: Optional[List[Middleware]] = None,
        name: Optional[str] = None,
        opt: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """WebSocket Route Handler decorator. Use this decorator to decorate
        websocket handler functions.

        Args:
            dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            middleware: A list of [Middleware][starlite.types.Middleware].
            name: A string identifying the route handler.
            opt: A string key dictionary of arbitrary values that can be accessed [Guards][starlite.types.Guard].
            path: A path fragment for the route handler function or a list of path fragments. If not given defaults to '/'
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
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

    def __call__(self, fn: "AsyncAnyCallable") -> "WebsocketRouteHandler":
        """Replaces a function with itself."""
        self.fn = fn
        self._validate_handler_function()
        return self

    def _validate_handler_function(self) -> None:
        """Validates the route handler function once it's set by inspecting its
        return annotations."""
        super()._validate_handler_function()

        fn = cast("AnyCallable", self.fn)
        signature = Signature.from_callable(fn)

        if signature.return_annotation is not None:
            raise ImproperlyConfiguredException("Websocket handler functions should return 'None'")
        if "socket" not in signature.parameters:
            raise ImproperlyConfiguredException("Websocket handlers must set a 'socket' kwarg")
        if "request" in signature.parameters:
            raise ImproperlyConfiguredException("The 'request' kwarg is not supported with websocket handlers")
        if "data" in signature.parameters:
            raise ImproperlyConfiguredException("The 'data' kwarg is not supported with websocket handlers")
        if not is_async_callable(fn):
            raise ImproperlyConfiguredException("Functions decorated with 'websocket' must be async functions")


websocket = WebsocketRouteHandler
