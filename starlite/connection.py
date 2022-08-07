from typing import TYPE_CHECKING, Any, Dict, Generic, TypeVar, cast

from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps, loads
from starlette.requests import Request as StarletteRequest
from starlette.websockets import WebSocket as StarletteWebSocket
from starlette.websockets import WebSocketState

from starlite.exceptions import ImproperlyConfiguredException, InternalServerException
from starlite.parsers import parse_query_params

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.types import Method

User = TypeVar("User")
Auth = TypeVar("Auth")


class Request(StarletteRequest, Generic[User, Auth]):
    @property
    def app(self) -> "Starlite":
        return cast("Starlite", self.scope["app"])

    @property
    def user(self) -> User:
        if "user" not in self.scope:
            raise ImproperlyConfiguredException("'user' is not defined in scope, install an AuthMiddleware to set it")
        return cast("User", self.scope["user"])

    @property
    def auth(self) -> Auth:
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException("'auth' is not defined in scope, install an AuthMiddleware to set it")
        return cast("Auth", self.scope["auth"])

    @property
    def query_params(self) -> Dict[str, Any]:  # type: ignore[override]
        return parse_query_params(self)

    @property
    def method(self) -> "Method":
        return cast("Method", self.scope["method"])

    async def json(self) -> Any:
        """
        Method to retrieve the json request body from the request.

        This method overrides the Starlette method using the much faster orjson.loads() function
        """
        if not hasattr(self, "_json"):
            body = self.scope.get("_body")
            if not body:
                body = self.scope["_body"] = await self.body()
            self._json = loads(body or "null")  # pylint: disable=attribute-defined-outside-init
        return self._json


class WebSocket(StarletteWebSocket, Generic[User, Auth]):
    @property
    def app(self) -> "Starlite":
        return cast("Starlite", self.scope["app"])

    @property
    def user(self) -> User:
        if "user" not in self.scope:
            raise ImproperlyConfiguredException("'user' is not defined in scope, install an AuthMiddleware to set it")
        return cast("User", self.scope["user"])

    @property
    def auth(self) -> Auth:
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException("'auth' is not defined in scope, install an AuthMiddleware to set it")
        return cast("Auth", self.scope["auth"])

    @property
    def query_params(self) -> Dict[str, Any]:  # type: ignore[override]
        return parse_query_params(self)

    async def receive_json(self, mode: str = "text") -> Any:
        """
        Exact copy of the `starlette` method, but using `orjson.loads()`.
        """
        if mode not in {"text", "binary"}:
            raise InternalServerException('The "mode" argument should be "text" or "binary".')
        if self.application_state != WebSocketState.CONNECTED:
            raise InternalServerException('WebSocket is not connected. Need to call "accept" first.')
        message = await self.receive()
        self._raise_on_disconnect(message)

        if mode == "text":
            text = message["text"]
        else:
            text = message["bytes"].decode("utf-8")
        return loads(text)

    async def send_json(self, data: Any, mode: str = "text") -> None:
        """
        Exact copy of the `starlette` method, but using `orjson.dumps()`.
        """
        if mode not in {"text", "binary"}:
            raise InternalServerException('The "mode" argument should be "text" or "binary".')
        binary = dumps(data, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS)
        if mode == "text":
            await self.send({"type": "websocket.send", "text": binary.decode("utf-8")})
        else:
            await self.send({"type": "websocket.send", "bytes": binary})
