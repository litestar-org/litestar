import re
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Pattern, Union

from typing_extensions import Protocol, runtime_checkable

from starlite.enums import ScopeType
from starlite.middleware.utils import should_bypass_middleware

if TYPE_CHECKING:
    from starlite.types import Scopes
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


class AbstractMiddleware:
    scopes: "Scopes" = {ScopeType.HTTP, ScopeType.WEBSOCKET}
    exclude: Optional[Union[str, List[str]]] = None
    exclude_opt_key: Optional[str] = None

    def __init__(
        self,
        app: "ASGIApp",
        exclude: Optional[Union[str, List[str]]] = None,
        exclude_opt_key: Optional[str] = None,
        scopes: Optional["Scopes"] = None,
    ) -> None:
        """

        Args:
            app: The 'next' ASGI app to call.
            exclude: A pattern or list of patterns to match against a request's path.
                If a match is found, the middleware will be skipped. .
            exclude_opt_key: An identifier that is set in the route handler
                'opt' key which allows skipping the middleware.
            scopes: ASGI scope types, should be a set including
                either or both 'ScopeType.HTTP' and 'ScopeType.WEBSOCKET'.
        """
        self.app = app
        self.scopes = scopes or self.scopes
        self.exclude_opt_key = exclude_opt_key or self.exclude_opt_key

        self.exclude_pattern: Optional[Pattern] = None

        exclude = exclude or self.exclude
        if exclude is not None:
            self.exclude_pattern = re.compile("|".join(exclude)) if isinstance(exclude, list) else re.compile(exclude)

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        original__call__ = cls.__call__

        async def wrapped_call(self: AbstractMiddleware, scope: "Scope", receive: "Receive", send: "Send") -> None:
            if should_bypass_middleware(
                scope=scope,
                scopes=self.scopes,
                exclude_path_pattern=self.exclude_pattern,
                exclude_opt_key=self.exclude_opt_key,
            ):
                await self.app(scope, receive, send)
            else:
                await original__call__(self, scope, receive, send)

        # https://github.com/python/mypy/issues/2427#issuecomment-384229898
        setattr(cls, "__call__", wrapped_call)  # noqa: B010

    @abstractmethod
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
        raise NotImplementedError("abstract method must be implemented")
