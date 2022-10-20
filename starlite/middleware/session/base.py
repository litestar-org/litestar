import abc
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Optional,
    TypeVar,
    cast,
)

from orjson import OPT_SERIALIZE_NUMPY, dumps, loads

from starlite import ASGIConnection
from starlite.middleware.base import MiddlewareProtocol
from starlite.utils import default_serializer, get_serializer_from_scope
from copy import deepcopy

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Message, Receive, Scope, Send
    from .config import CookieConfig


C = TypeVar("C", bound="CookieConfig")


class SessionBackend(abc.ABC, Generic[C]):
    def __init__(self, config: C) -> None:
        self.config = config

    @staticmethod
    def serialise_data(data: Any, scope: Optional["Scope"] = None) -> bytes:
        """
        Serialise data into bytes for storage in the backend. The serialiser will be
        gathered from `scope` and fall back to [default_serializer][starlite.utils.default_serializer]
        """
        serializer = (get_serializer_from_scope(scope) if scope else None) or default_serializer
        return dumps(data, default=serializer, option=OPT_SERIALIZE_NUMPY)

    @staticmethod
    def deserialise_data(data: Any) -> Dict[str, Any]:
        return cast(Dict[str, Any], loads(data))

    @abc.abstractmethod
    async def store_session(self, message: "Message", connection: ASGIConnection) -> None:
        pass

    @abc.abstractmethod
    async def load_session(self, connection: ASGIConnection) -> Dict[str, Any]:
        pass


class BaseSessionMiddleware(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp", backend: SessionBackend) -> None:
        self.app = app
        self.backend = backend

    def create_send_wrapper(self, connection: ASGIConnection) -> Callable[["Message"], Awaitable[None]]:
        """
        Creates a wrapper for the ASGI send function, which handles setting the cookies on the outgoing response.
        Args:
            connection: ASGIConnection

        Returns:
            None.
        """

        async def wrapped_send(message: "Message") -> None:
            """A wrapper around the send function, declared in local scope to
            use closure values.

            Args:
                message: An ASGI message.

            Returns:
                None
            """
            if message["type"] != "http.response.start":
                await connection.send(message)
                return

            await self.backend.store_session(message, connection)
            await connection.send(message)

        return wrapped_send

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """
        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        if scope["type"] in self.backend.config.scopes:
            our_scope = deepcopy(scope)  # copy scope before mutating it as per ASGI spec
            connection = ASGIConnection[Any, Any, Any](our_scope, receive=receive, send=send)
            our_scope["session"] = await self.backend.load_session(connection)

            await self.app(our_scope, receive, self.create_send_wrapper(connection))
        else:
            await self.app(scope, receive, send)
