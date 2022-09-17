from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import parse_qsl

from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps, loads
from starlette.datastructures import URL, URLPath
from starlette.requests import Request as StarletteRequest
from starlette.websockets import WebSocket as StarletteWebSocket
from starlette.websockets import WebSocketState
from starlite_multipart import MultipartFormDataParser
from starlite_multipart import UploadFile as MultipartUploadFile
from starlite_multipart import parse_options_header

from starlite.datastructures import FormMultiDict, UploadFile
from starlite.enums import RequestEncodingType
from starlite.exceptions import ImproperlyConfiguredException, InternalServerException
from starlite.parsers import parse_query_params
from starlite.types import Empty, EmptyType, HTTPScope, Message, WebSocketScope

if TYPE_CHECKING:
    from pydantic import BaseModel
    from starlette.requests import HTTPConnection
    from typing_extensions import Literal

    from starlite.app import Starlite
    from starlite.handlers.http import HTTPRouteHandler  # noqa: F401
    from starlite.handlers.websocket import WebsocketRouteHandler  # noqa: F401
    from starlite.types import Method, Receive, Scope, Send

User = TypeVar("User")
Auth = TypeVar("Auth")
Handler = TypeVar("Handler")


async def empty_receive() -> Any:  # pragma: no cover
    """Placeholder value.

    Raises:
        RuntimeError
    """
    raise RuntimeError()


async def empty_send(_: Message) -> None:  # pragma: no cover
    """Placeholder value.

    Args:
        _: An ASGI message

    Raises:
        RuntimeError
    """
    raise RuntimeError()


class AppMixin:
    scope: "Scope"

    @property
    def app(self) -> "Starlite":
        """
        Returns:
            The [Starlite][starlite.app.Starlite] application instance
        """
        return self.scope["app"]


class RouteHandlerMixin(Generic[Handler]):
    scope: "Scope"

    @property
    def route_handler(self) -> Handler:
        """
        Returns:
            The target route handler
        """
        return cast("Handler", self.scope["route_handler"])


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
        self.scope["session"] = value

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
            self._url = URL(scope=self.scope)  # type: ignore[arg-type]
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
        starlite_instance = self.scope["app"]
        index = starlite_instance.get_handler_index_by_name(name)
        if index:
            return URLPath(index["path"]).make_absolute_url(self.base_url)
        return None


class Request(URLMixin, AppMixin, RouteHandlerMixin["HTTPRouteHandler"], SessionMixin, Generic[User, Auth], AuthMixin[User, Auth], QueryParamMixin, StarletteRequest):  # type: ignore[misc]
    scope: "HTTPScope"  # type: ignore[assignment]

    def __init__(self, scope: "HTTPScope", receive: "Receive" = empty_receive, send: "Send" = empty_send):
        """The Starlite Request class.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
        """
        super().__init__(scope, receive, send)  # type: ignore[arg-type]
        self._json: Any = Empty
        self._form: Union[FormMultiDict, EmptyType] = Empty  # type: ignore[assignment]

    @property
    def method(self) -> "Method":
        """
        Returns:
            The request [Method][starlite.types.Method]
        """
        return self.scope["method"]

    @property
    def content_type(self) -> Tuple[str, Dict[str, str]]:
        """Parses the request's 'Content-Type' header, returning the header
        value and any options as a dictionary.

        Returns:
            A tuple with the parsed value and a dictionary containing any options send in it.
        """
        return parse_options_header(self.headers.get("Content-Type"))

    async def json(self) -> Any:
        """Method to retrieve the json request body from the request.

        This method overrides the Starlette method using the much faster orjson.loads() function

        Returns:
            An arbitrary value
        """
        if self._json is Empty:
            if "_body" not in self.scope:
                body = self.scope["_body"] = (await self.body()) or b"null"  # type: ignore[typeddict-item]
            else:
                body = self.scope["_body"]  # type: ignore[typeddict-item]
            self._json = loads(body)
        return self._json

    async def form(self) -> FormMultiDict:  # type: ignore[override]
        """Method to retrieve form data from the request. If the request is
        either a 'multipart/form-data' or an 'application/x-www-form-
        urlencoded', this method will return a FormData instance populated with
        the values sent in the request. Otherwise, an empty instance is
        returned.

        Returns:
            A FormData instance.
        """
        if self._form is Empty:
            content_type, options = self.content_type
            if content_type == RequestEncodingType.MULTI_PART:
                parser = MultipartFormDataParser(headers=self.headers, stream=self.stream(), max_file_size=None)
                form_values = await parser()
                form_values = [
                    (
                        k,
                        UploadFile(
                            filename=v.filename,
                            content_type=v.content_type,
                            headers=v.headers,
                            file=v.file,  # type: ignore[arg-type]
                        )
                        if isinstance(v, MultipartUploadFile)
                        else v,
                    )
                    for k, v in form_values
                ]
                self._form = FormMultiDict(form_values)

            elif content_type == RequestEncodingType.URL_ENCODED:
                self._form = FormMultiDict(
                    parse_qsl(
                        b"".join([chunk async for chunk in self.stream()]).decode(options.get("charset", "latin-1"))
                    )
                )
            else:
                self._form = FormMultiDict()
        return cast("FormMultiDict", self._form)


class WebSocket(  # type: ignore[misc]
    URLMixin,
    AppMixin,
    SessionMixin,
    RouteHandlerMixin["WebsocketRouteHandler"],
    Generic[User, Auth],
    AuthMixin[User, Auth],
    QueryParamMixin,
    StarletteWebSocket,
):
    scope: "WebSocketScope"  # type: ignore[assignment]

    def __init__(self, scope: "WebSocketScope", receive: "Receive" = empty_receive, send: "Send" = empty_send) -> None:
        """The Starlite WebSocket class.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
        """
        super().__init__(scope, receive, send)  # type: ignore[arg-type]
        self.scope = scope

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
