from inspect import Signature
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from pydantic import validate_arguments

from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers.base import BaseRouteHandler
from starlite.types import AsyncAnyCallable, ExceptionHandlersMap, Guard
from starlite.utils import Ref, is_async_callable

if TYPE_CHECKING:
    from starlite.types import MaybePartial  # nopycln: import # noqa: F401


class ASGIRouteHandler(BaseRouteHandler["ASGIRouteHandler"]):
    """ASGI Route Handler decorator.

    Use this decorator to decorate ASGI applications.
    """

    __slots__ = ("is_mount", "is_static")

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        exception_handlers: Optional[ExceptionHandlersMap] = None,
        guards: Optional[List[Guard]] = None,
        name: Optional[str] = None,
        opt: Optional[Dict[str, Any]] = None,
        is_mount: bool = False,
        is_static: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize `ASGIRouteHandler`.

        Args:
            exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
            guards: A list of [Guard][starlite.types.Guard] callables.
            name: A string identifying the route handler.
            opt: A string key dictionary of arbitrary values that can be accessed in [Guards][starlite.types.Guard] or
                wherever you have access to [Request][starlite.connection.request.Request] or [ASGI Scope][starlite.types.Scope].
            path: A path fragment for the route handler function or a list of path fragments. If not given defaults to '/'
            is_mount: A boolean dictating whether the handler's paths should be regarded as mount paths. Mount path accept
                any arbitrary paths that begin with the defined prefixed path. For example, a mount with the path `/some-path/`
                will accept requests for `/some-path/` and any sub path under this, e.g. `/some-path/sub-path/` etc.
            is_static: A boolean dictating whether the handler's paths should be regarded as static paths. Static paths
                are used to deliver static files.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        self.is_mount = is_mount or is_static
        self.is_static = is_static
        super().__init__(path, exception_handlers=exception_handlers, guards=guards, name=name, opt=opt, **kwargs)

    def __call__(self, fn: "AsyncAnyCallable") -> "ASGIRouteHandler":
        """Replace a function with itself."""
        self.fn = Ref["MaybePartial[AsyncAnyCallable]"](fn)
        self.signature = Signature.from_callable(fn)
        self._validate_handler_function()
        return self

    def _validate_handler_function(self) -> None:
        """Validate the route handler function once it's set by inspecting its return annotations."""
        super()._validate_handler_function()

        if self.signature.return_annotation not in {None, "None"}:
            raise ImproperlyConfiguredException("ASGI handler functions should return 'None'")

        if any(key not in self.signature.parameters for key in ("scope", "send", "receive")):
            raise ImproperlyConfiguredException(
                "ASGI handler functions should define 'scope', 'send' and 'receive' arguments"
            )
        if not is_async_callable(self.fn.value):
            raise ImproperlyConfiguredException("Functions decorated with 'asgi' must be async functions")


asgi = ASGIRouteHandler
