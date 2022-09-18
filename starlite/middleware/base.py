from typing import TYPE_CHECKING, Any, Callable

from typing_extensions import Protocol, runtime_checkable

if TYPE_CHECKING:
    from starlite.types.asgi_types import ASGIApp, Receive, Scope, Send


@runtime_checkable
class MiddlewareProtocol(Protocol):  # pragma: no cover
    __slots__ = ("app",)

    app: "ASGIApp"

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """Executes the ASGI middleware.

        Called by the previous middleware in the stack if a response is not awaited prior.

        Upon completion, middleware should call the next ASGI handler and await it - or await a response created in its
        closure.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """


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
        """Calls the middleware constructor or factory.

        Args:
            app: An ASGIApp, this value is the next ASGI handler to call in the middleware stack.

        Returns:
            Calls 'self.middleware' and returns the ASGIApp created.
        """

        return self.middleware(*self.args, app=app, **self.kwargs)
