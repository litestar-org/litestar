from typing import TYPE_CHECKING, Any, Dict, Generic, Optional, TypeVar, Union, cast

from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps, loads
from starlette.datastructures import URL, URLPath
from starlette.requests import Request as StarletteRequest
from starlette.requests import empty_receive, empty_send
from starlette.websockets import WebSocket as StarletteWebSocket
from starlette.websockets import WebSocketState

from starlite.exceptions import ImproperlyConfiguredException, InternalServerException
from starlite.parsers import parse_query_params
from starlite.types import Empty

if TYPE_CHECKING:
    from pydantic import BaseModel
    from starlette.requests import HTTPConnection
    from typing_extensions import Literal

    from starlite.app import Starlite
    from starlite.types import Method, Receive, Scope, Send

User = TypeVar("User")
Auth = TypeVar("Auth")


class AppMixin:
    scope: "Scope"

    @property
    def app(self) -> "Starlite":
        """
        Returns:
            The [Starlite][starlite.app.Starlite] application instance
        """
        return cast("Starlite", self.scope["app"])


class SessionMixin:
    scope: "Scope"

    @property
    def session(self) -> Dict[str, Any]:
        """
        Returns:
            A dictionary representing the session value - if existing.

        Raises:
            ImproperlyConfiguredException: if session is not set in scope.
        """
        if "session" not in self.scope:
            raise ImproperlyConfiguredException(
                "'session' is not defined in scope, install a SessionMiddleware to set it"
            )
        return cast("Dict[str, Any]", self.scope["session"])

    def set_session(self, value: Union[Dict[str, Any], "BaseModel"]) -> None:
        """Helper method to set the session in scope.

        If the [Starlite SessionMiddleware][starlite.middleware.base.session.SessionMiddleware] is
        enabled, the session will be added to the response as a cookie header.

        Args:
            value: Dictionary or pydantic model instance for the session data.

        Returns:
            None.
        """
        self.scope.update(session=value)

    def clear_session(self) -> None:
        """Helper method to remove the session from scope.

        If the [Starlite SessionMiddleware][starlite.middleware.base.session.SessionMiddleware] is
        enabled, this will cause the session data to be cleared.

        Returns:
            None.
        """
        self.scope["session"] = Empty


class AuthMixin(Generic[User, Auth]):
    scope: "Scope"

    @property
    def user(self) -> User:
        """Allows access to user data.

        Raises:
            ImproperlyConfiguredException: If 'user' is not set in scope via an 'AuthMiddleware', raises an exception

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
            ImproperlyConfiguredException: If 'auth' is not set in scope via an 'AuthMiddleware', raises an exception

        Returns:
            A type correlating to the generic variable Auth.
        """
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException("'auth' is not defined in scope, install an AuthMiddleware to set it")
        return cast("Auth", self.scope["auth"])


class QueryParamMixin:
    scope: "Scope"
    _parsed_query: Dict[str, Any]

    @property
    def query_params(self) -> Dict[str, Any]:
        """
        Returns:
            A normalized dict of query parameters. Multiple values for the same key are returned as a list.
        """
        if not hasattr(self, "_parsed_query"):
            self._parsed_query = parse_query_params(cast("HTTPConnection", self))
        return self._parsed_query


class URLMixin:
    scope: "Scope"
    _base_url: URL
    _url: URL

    @property
    def url(self) -> URL:
        """

        Returns:
            A URL instance constructed from the request's scope.
        """
        if not hasattr(self, "_url"):
            self._url = URL(scope=self.scope)
        return self._url

    @property
    def base_url(self) -> URL:
        """

        Returns:
            A URL instance constructed from the request's scope, representing only the base part
            (host + domain + prefix) of the request.
        """
        if not hasattr(self, "_base_url"):
            self._base_url = URL(
                scope={
                    **self.scope,
                    "path": "/",
                    "query_string": b"",
                    "root_path": self.scope.get("app_root_path") or self.scope.get("root_path", ""),
                }
            )
        return self._base_url

    def url_for(self, name: str) -> Optional[str]:
        """

        Args:
            name: The 'name' of the request route handler.

        Returns:
            If a route handler with the given name is found, it returns a string representing the absolute url of the
            route handler.
        """
        starlite_instance = cast("Starlite", self.scope["app"])
        index = starlite_instance.get_handler_index_by_name(name)
        if index:
            return URLPath(index["path"]).make_absolute_url(self.base_url)
        return None


class Request(URLMixin, AppMixin, SessionMixin, Generic[User, Auth], AuthMixin[User, Auth], QueryParamMixin, StarletteRequest):  # type: ignore[misc]
    """The Starlite Request class."""

    def __init__(self, scope: "Scope", receive: "Receive" = empty_receive, send: "Send" = empty_send):
        super().__init__(scope, receive, send)
        self._json: Any = Empty

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


class WebSocket(  # type: ignore[misc]
    URLMixin, AppMixin, SessionMixin, Generic[User, Auth], AuthMixin[User, Auth], QueryParamMixin, StarletteWebSocket
):
    """The Starlite WebSocket class."""

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
