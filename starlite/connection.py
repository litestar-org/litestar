from typing import TYPE_CHECKING, Any, Dict, Generic, TypeVar, cast

from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps, loads
from starlette.requests import Request as StarletteRequest
from starlette.requests import empty_receive, empty_send
from starlette.websockets import WebSocket as StarletteWebSocket
from starlette.websockets import WebSocketState

from starlite.exceptions import ImproperlyConfiguredException, InternalServerException
from starlite.parsers import parse_query_params
from starlite.types import Empty

if TYPE_CHECKING:
    from starlette.types import Receive, Scope, Send
    from typing_extensions import Literal

    from starlite.app import Starlite
    from starlite.types import Method

User = TypeVar("User")
Auth = TypeVar("Auth")


class Request(StarletteRequest, Generic[User, Auth]):
    """The Starlite Request class."""

    def __init__(self, scope: "Scope", receive: "Receive" = empty_receive, send: "Send" = empty_send):
        super().__init__(scope, receive, send)
        self._json: Any = Empty

    @property
    def app(self) -> "Starlite":
        """
        Returns:
            The [Starlite][starlite.app.Starlite] application instance
        """
        return cast("Starlite", self.scope["app"])

    @property
    def user(self) -> User:
        """Allows access to user data.

        Raises:
            [ImproperlyConfiguredException][starlite.exceptions.ImproperlyConfiguredException]: If 'user' is not set in scope via an 'AuthMiddleware', raises an exception

        Returns:
            A type correlating to the generic variable User.
        """
        if "user" not in self.scope:
            raise ImproperlyConfiguredException("'user' is not defined in scope, install an AuthMiddleware to set it")
        return cast("User", self.scope["user"])

    @property
    def auth(self) -> Auth:
        """Allows access to auth data.

        Raises:
            [ImproperlyConfiguredException][starlite.exceptions.ImproperlyConfiguredException]: If 'auth' is not set in scope via an 'AuthMiddleware', raises an exception

        Returns:
            A type correlating to the generic variable Auth.
        """
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException("'auth' is not defined in scope, install an AuthMiddleware to set it")
        return cast("Auth", self.scope["auth"])

    @property
    def query_params(self) -> Dict[str, Any]:  # type: ignore[override]
        """
        Returns:
            A normalized dict of query parameters. Multiple values for the same key are returned as a list.
        """
        return parse_query_params(self)

    @property
    def method(self) -> "Method":
        """

        Returns:
            The request [Method][starlite.types.Method]
        """
        return cast("Method", self.scope["method"])

    async def json(self) -> Any:
        """Method to retrieve the json request body from the request.

        This method overrides the Starlette method using the much faster orjson.loads() function

        Returns:
            An arbitrary value
        """
        if self._json is Empty:
            if "_body" not in self.scope:
                body = self.scope["_body"] = (await self.body()) or b"null"
            else:
                body = self.scope["_body"]
            self._json = loads(body)
        return self._json


class WebSocket(StarletteWebSocket, Generic[User, Auth]):
    """The Starlite WebSocket class."""

    @property
    def app(self) -> "Starlite":
        """
        Returns:
            The [Starlite][starlite.app.Starlite] application instance
        """
        return cast("Starlite", self.scope["app"])

    @property
    def user(self) -> User:
        """Allows access to user data.

        Raises:
            [ImproperlyConfiguredException][starlite.exceptions.ImproperlyConfiguredException]: If 'user' is not set in scope via an 'AuthMiddleware', raises an exception

        Returns:
            A type correlating to the generic variable User.
        """
        if "user" not in self.scope:
            raise ImproperlyConfiguredException("'user' is not defined in scope, install an AuthMiddleware to set it")
        return cast("User", self.scope["user"])

    @property
    def auth(self) -> Auth:
        """Allows access to auth data.

        Raises:
            [ImproperlyConfiguredException][starlite.exceptions.ImproperlyConfiguredException]: If 'auth' is not set in scope via an 'AuthMiddleware', raises an exception

        Returns:
            A type correlating to the generic variable Auth.
        """
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException("'auth' is not defined in scope, install an AuthMiddleware to set it")
        return cast("Auth", self.scope["auth"])

    @property
    def query_params(self) -> Dict[str, Any]:  # type: ignore[override]
        """
        Returns:
            A normalized dict of query parameters. Multiple values for the same key are returned as a list.
        """
        return parse_query_params(self)

    async def receive_json(self, mode: "Literal['text', 'binary']" = "text") -> Any:  # type: ignore
        """Receives data and loads it into JSON using orson.

        Args:
            mode: Either 'text' or 'binary'.

        Returns:
            An arbitrary value
        """
        if mode not in {"text", "binary"}:
            raise ImproperlyConfiguredException('The "mode" argument should be "text" or "binary".')
        if self.application_state != WebSocketState.CONNECTED:
            raise InternalServerException('WebSocket is not connected. Need to call "accept" first.')
        message = await self.receive()
        self._raise_on_disconnect(message)

        if mode == "text":
            text = message["text"]
        else:
            text = message["bytes"].decode("utf-8")
        return loads(text)

    async def send_json(self, data: Any, mode: "Literal['text', 'binary']" = "text") -> None:  # type: ignore
        """Sends data as JSON.

        Args:
            data: A value to serialize.
            mode: Either 'text' or 'binary'.

        Returns:
            None
        """
        if mode not in {"text", "binary"}:
            raise ImproperlyConfiguredException('The "mode" argument should be "text" or "binary".')
        binary = dumps(data, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS)
        if mode == "text":
            await self.send({"type": "websocket.send", "text": binary.decode("utf-8")})
        else:
            await self.send({"type": "websocket.send", "bytes": binary})
