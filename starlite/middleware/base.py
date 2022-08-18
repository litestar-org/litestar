from typing import TYPE_CHECKING, Any, Callable, Dict, Protocol, runtime_checkable

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send


@runtime_checkable
class MiddlewareProtocol(Protocol):  # pragma: no cover
    def __init__(self, app: "ASGIApp", **kwargs: Dict[str, Any]):
        ...

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        ...


class DefineMiddleware:
    __slots__ = (
        "middleware",
        "args",
        "kwargs",
    )

    def __init__(self, middleware: Callable[..., "ASGIApp"], *args: Any, **kwargs: Any) -> None:
        """This class is a container that allows passing *args and **kwargs to
        Middleware class constructors and factory functions.

        Args:
            middleware: A callable that returns an ASGIApp.
            *args: Positional arguments to pass to the callable.
            **kwargs: Key word arguments to pass to the callable.

        Notes:
            The callable will be passed a kwarg `app`, which is the next ASGI app to call in the middleware stack.
            It therefore must define such a kwarg.
        """
        self.middleware = middleware
        self.args = args
        self.kwargs = kwargs

    def __call__(self, app: "ASGIApp") -> "ASGIApp":
        return self.middleware(*self.args, app=app, **self.kwargs)
