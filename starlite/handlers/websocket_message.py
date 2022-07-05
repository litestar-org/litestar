from inspect import Signature
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, validate_arguments
from pydantic.typing import AnyCallable

from starlite.connection import WebSocket
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.provide import Provide
from starlite.types import ExceptionHandler, Guard, Middleware
from starlite.utils import is_async_callable

from .base import BaseRouteHandler

T_model = TypeVar("T_model", bound=BaseModel)


class WSMessageHandler(BaseRouteHandler):
    """
    A websocket handler that wraps the handler function in a function that manages the open
    websocket.

    Handlers must specify the `data` kwarg with the type that messages should be coerced to.

    Handlers may specify the `socket` kwarg, however any method on the socket that results
    in `receive()` being called are not allowed to be called.

    As many properties of the `HTTPRouteHandler` are supported, however they wrap the
    socket connection, not each message.

    A second set of properties that wrap the message are available.

    Thinking
    --------
    - should I just use after_request and before_request as after_disconnect and before_accept?
    """

    __slots__ = (
        "handler_fn",
        "before_accept",
        "after_disconnect",
        "before_message",
        "after_message",
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        before_accept: Optional[Callable[[WebSocket], WebSocket]] = None,
        after_disconnect: Optional[Callable[[WebSocket], WebSocket]] = None,
        before_message: Optional[Callable[[Any], Any]] = None,
        after_message: Optional[Callable[[Any], Any]] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        middleware: Optional[List[Middleware]] = None,
        opt: Optional[Dict[str, Any]] = None,
        path: Union[Optional[str], Optional[List[str]]] = None,
    ) -> None:
        self.before_accept = before_accept
        self.after_disconnect = after_disconnect
        self.before_message = before_message
        self.after_message = after_message
        super().__init__(
            dependencies=dependencies,
            exception_handlers=exception_handlers,
            guards=guards,
            middleware=middleware,
            opt=opt,
            path=path,
        )

    def __call__(self, fn: AnyCallable) -> "WSMessageHandler":
        """
        Replaces a function with itself
        """
        self.fn = fn
        self.validate_handler_function()
        return self

    def resolve_before_accept(self) -> None:
        """TODO"""

    def resolve_after_disconnect(self) -> None:
        """TODO"""

    def resolve_before_message(self) -> None:
        """TODO"""

    def resolve_after_message(self) -> None:
        """TODO"""

    def validate_handler_function(self) -> None:
        """
        Validate the parameters of the handler function.
        """
        super().validate_handler_function()
        signature = Signature.from_callable(self.fn)  # type:ignore[arg-type]
        return_annotation = signature.return_annotation
        if return_annotation is Signature.empty:
            raise ValidationException("Return value of `ws` handler function must be annotated.")
        if "data" not in signature.parameters:
            raise ImproperlyConfiguredException("The 'data' kwarg must be specified for ws_messge handlers")
        if "request" in signature.parameters:
            raise ImproperlyConfiguredException("The 'request' kwarg is not supported with ws_message handlers")
        if not is_async_callable(self.fn):
            raise ImproperlyConfiguredException("Functions decorated with 'websocket' must be async functions")


ws_message = WSMessageHandler
