from inspect import Signature
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from pydantic import validate_arguments

from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers.base import BaseRouteHandler
from starlite.types import ExceptionHandlersMap, Guard
from starlite.utils import is_async_callable

if TYPE_CHECKING:
    from starlite.types import AnyCallable


class ASGIRouteHandler(BaseRouteHandler["ASGIRouteHandler"]):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        exception_handlers: Optional[ExceptionHandlersMap] = None,
        guards: Optional[List[Guard]] = None,
        name: Optional[str] = None,
        opt: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """ASGI Route Handler decorator. Use this decorator to decorate ASGI
        apps.

        Args:
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            name: A string identifying the route handler.
            opt: A string key dictionary of arbitrary values that can be accessed [Guards][starlite.types.Guard].
            path: A path fragment for the route handler function or a list of path fragments. If not given defaults to '/'
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        super().__init__(path, exception_handlers=exception_handlers, guards=guards, name=name, opt=opt, **kwargs)

    def __call__(self, fn: "AnyCallable") -> "ASGIRouteHandler":
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
            raise ImproperlyConfiguredException("ASGI handler functions should return 'None'")
        if any(key not in signature.parameters for key in ("scope", "send", "receive")):
            raise ImproperlyConfiguredException(
                "ASGI handler functions should define 'scope', 'send' and 'receive' arguments"
            )
        if not is_async_callable(fn):
            raise ImproperlyConfiguredException("Functions decorated with 'asgi' must be async functions")


asgi = ASGIRouteHandler
