from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)
from urllib.parse import parse_qsl

from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps, loads
from starlette.datastructures import URL, Address, Headers, URLPath
from starlette.requests import SERVER_PUSH_HEADERS_TO_COPY, cookie_parser
from starlite_multipart import MultipartFormDataParser
from starlite_multipart import UploadFile as MultipartUploadFile
from starlite_multipart import parse_options_header

from starlite.datastructures import FormMultiDict, State, UploadFile
from starlite.enums import RequestEncodingType
from starlite.exceptions import ImproperlyConfiguredException, InternalServerException
from starlite.parsers import parse_query_params
from starlite.types import (
    Empty,
    EmptyType,
    HTTPScope,
    Message,
    Serializer,
    WebSocketScope,
)
from starlite.utils.serialization import default_serializer

if TYPE_CHECKING:
    from typing import BinaryIO, MutableMapping

    from pydantic import BaseModel
    from typing_extensions import Literal

    from starlite.app import Starlite
    from starlite.handlers.http import HTTPRouteHandler  # noqa: F401
    from starlite.handlers.websocket import WebsocketRouteHandler  # noqa: F401
    from starlite.types.asgi_types import (
        Method,
        Receive,
        ReceiveMessage,
        Scope,
        Send,
        WebSocketAcceptEvent,
        WebSocketCloseEvent,
        WebSocketReceiveEvent,
        WebSocketSendEvent,
    )

User = TypeVar("User")
Auth = TypeVar("Auth")
HandlerType = TypeVar("HandlerType")


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


class ASGIConnection(Generic[HandlerType, User, Auth]):
    __slots__ = ("scope", "receive", "send", "_base_url", "_url", "_parsed_query", "_headers", "_cookies")

    def __init__(self, scope: "Scope", receive: "Receive" = empty_receive, send: "Send" = empty_send):
        self.scope = scope
        self.receive = receive
        self.send = send
        self._base_url: Union[Any, EmptyType] = scope.get("_base_url", Empty)
        self._url: Union[Any, EmptyType] = scope.get("_url", Empty)
        self._parsed_query: Union[Any, EmptyType] = scope.get("_parsed_query", Empty)
        self._cookies: Union[Any, EmptyType] = scope.get("_cookies", Empty)
        self._headers: Union[Any, EmptyType] = scope.get("_headers", Empty)

    @property
    def app(self) -> "Starlite":
        """
        Returns:
            The [Starlite][starlite.app.Starlite] application instance
        """
        return self.scope["app"]

    @property
    def route_handler(self) -> HandlerType:
        """
        Returns:
            The target route handler instance.
        """
        return cast("HandlerType", self.scope["route_handler"])

    @property
    def state(self) -> State:
        """

        Returns:
            A State instance constructed from the scope["state"] value.
        """
        return State(self.scope["state"])

    @property
    def url(self) -> URL:
        """

        Returns:
            A URL instance constructed from the request's scope.
        """
        if self._url is Empty:
            self._url = self.scope["_url"] = URL(scope=cast("MutableMapping[str, Any]", self.scope))  # type: ignore[typeddict-item]
        return cast("URL", self._url)

    @property
    def base_url(self) -> URL:
        """

        Returns:
            A URL instance constructed from the request's scope, representing only the base part
            (host + domain + prefix) of the request.
        """
        if self._base_url is Empty:
            self._base_url = self.scope["_base_url"] = URL(  # type: ignore[typeddict-item]
                scope={
                    **self.scope,
                    "path": "/",
                    "query_string": b"",
                    "root_path": self.scope.get("app_root_path") or self.scope.get("root_path", ""),
                }
            )
        return cast("URL", self._base_url)

    @property
    def headers(self) -> Headers:
        """

        Returns:
            A Headers instance with the request's scope["headers"] value.
        """
        if self._headers is Empty:
            self._headers = self.scope["_base_url"] = Headers(scope=self.scope)  # type: ignore[typeddict-item]
        return cast("Headers", self._headers)

    @property
    def query_params(self) -> Dict[str, Any]:
        """
        Returns:
            A normalized dict of query parameters. Multiple values for the same key are returned as a list.
        """
        if self._parsed_query is Empty:
            self._parsed_query = self.scope["_parsed_query"] = parse_query_params(self)  # type: ignore[typeddict-item]
        return cast("Dict[str, Any]", self._parsed_query)

    @property
    def path_params(self) -> Dict[str, Any]:
        """

        Returns:
            A string keyed dictionary of path parameter values.
        """
        return self.scope["path_params"]

    @property
    def cookies(self) -> Dict[str, str]:
        """
        Returns:
            Returns any cookies stored in the header as a parsed dictionary.
        """
        if self._cookies is Empty:
            cookies: Dict[str, str] = {}
            cookie_header = self.scope["_cookies"] = self.headers.get("cookie")  # type: ignore[typeddict-item]
            if cookie_header:
                cookies = cookie_parser(cookie_header)
            self._cookies = cookies
        return cast("Dict[str, str]", self._cookies)

    @property
    def client(self) -> Optional[Address]:
        """

        Returns:
            A two tuple of the host name and port number.
        """
        client = self.scope.get("client")
        return Address(*client) if client else None

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


class Request(Generic[User, Auth], ASGIConnection["HTTPRouteHandler", User, Auth]):
    __slots__ = ("_json", "_form", "_body", "is_connected")

    scope: "HTTPScope"

    def __init__(self, scope: "Scope", receive: "Receive" = empty_receive, send: "Send" = empty_send):
        """The Starlite Request class.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
        """

        super().__init__(scope, receive, send)
        self.is_connected: bool = True
        self._body: Union[Any, EmptyType] = scope.get("_body", Empty)
        self._form: Union[Any, EmptyType] = scope.get("_form", Empty)
        self._json: Union[Any, EmptyType] = scope.get("_json", Empty)

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
            self._json = self.scope["_json"] = loads((await self.body()) or b"null")  # type: ignore
        return self._json

    async def stream(self) -> AsyncGenerator[bytes, None]:
        """Returns an async generator that streams chunks of bytes.

        Returns:
            An async generator.

        Raises:
            RuntimeError: if the stream is already consumed
        """
        if isinstance(self._body, bytes):
            yield self._body
            yield b""
            return

        if not self.is_connected:
            raise RuntimeError("stream consumed")

        while self.is_connected:
            event = await self.receive()
            if event["type"] == "http.request":
                body = event.get("body", b"")
                if body:
                    yield body
                if not event.get("more_body", False):
                    break
            if event["type"] == "http.disconnect":
                raise InternalServerException("client disconnected prematurely")

        self.is_connected = False
        yield b""

    async def body(self) -> bytes:
        """
        Returns:
            A byte-string representing the body of the request.
        """
        if self._body is Empty:
            chunks = []
            async for chunk in self.stream():
                chunks.append(chunk)
            self._body = self.scope["_body"] = b"".join(chunks)  # type: ignore
        return cast("bytes", self._body)

    async def form(self) -> FormMultiDict:
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
                            file=cast("BinaryIO", v.file),
                        )
                        if isinstance(v, MultipartUploadFile)
                        else v,
                    )
                    for k, v in form_values
                ]
                self._form = self.scope["_form"] = FormMultiDict(form_values)  # type: ignore

            elif content_type == RequestEncodingType.URL_ENCODED:
                self._form = self.scope["_form"] = FormMultiDict(  # type: ignore
                    parse_qsl(
                        b"".join([chunk async for chunk in self.stream()]).decode(options.get("charset", "latin-1"))
                    )
                )
            else:
                self._form = self.scope["_form"] = FormMultiDict()  # type: ignore
        return cast("FormMultiDict", self._form)

    async def send_push_promise(self, path: str) -> None:
        """Sends a push promise. This method requires the 'http.response.push'
        extension to be sent from the ASGI server.

        Args:
            path: Path to send the promise to.

        Returns:
            None
        """
        extensions: Dict[str, Dict[Any, Any]] = self.scope.get("extensions") or {}
        if "http.response.push" in extensions:
            raw_headers = []
            for name in SERVER_PUSH_HEADERS_TO_COPY:
                for value in self.headers.getlist(name):
                    raw_headers.append((name.encode("latin-1"), value.encode("latin-1")))
            await self.send({"type": "http.response.push", "path": path, "headers": raw_headers})


class WebSocket(
    Generic[User, Auth],
    ASGIConnection["HTTPRouteHandler", User, Auth],
):
    __slots__ = ("connection_state",)

    scope: "WebSocketScope"

    def __init__(self, scope: "Scope", receive: "Receive" = empty_receive, send: "Send" = empty_send) -> None:
        """The Starlite WebSocket class.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
        """
        super().__init__(scope, self.receive_wrapper(receive), self.send_wrapper(send))
        self.connection_state: "Literal['init', 'connect', 'receive', 'disconnect']" = "init"

    def receive_wrapper(self, receive: "Receive") -> "Receive":
        """Wraps 'receive' to set 'self.connection_state' and validate events.

        Args:
            receive: The ASGI receive function.

        Returns:
            An ASGI receive function.
        """

        async def wrapped_receive() -> "ReceiveMessage":
            if self.connection_state == "disconnect":
                raise RuntimeError()
            message = await receive()
            if message["type"] == "websocket.connect":
                self.connection_state = "connect"
            elif message["type"] == "websocket.receive":
                self.connection_state = "receive"
            else:
                self.connection_state = "disconnect"
            return message

        return wrapped_receive

    def send_wrapper(self, send: "Send") -> "Send":
        """Wraps 'send' to ensure that state is not disconnected.

        Args:
            send: The ASGI send function.

        Returns:
            An ASGI send function.
        """

        async def wrapped_send(message: Message) -> None:
            if self.connection_state == "disconnect":
                raise RuntimeError()
            await send(message)

        return wrapped_send

    async def accept(
        self,
        sub_protocol: Optional[str] = None,
        headers: Optional[Union[Headers, List[Tuple[bytes, bytes]]]] = None,
    ) -> None:
        """Accepts the incoming connection. This method should be called before
        receiving data.

        Args:
            sub_protocol:
            headers:

        Returns:
        """
        if self.connection_state == "init":
            await self.receive()
            _headers: List[Tuple[bytes, bytes]] = headers if isinstance(headers, list) else []

            if isinstance(headers, Headers):
                _headers = headers.raw

            event: "WebSocketAcceptEvent" = {
                "type": "websocket.accept",
                "subprotocol": sub_protocol,
                "headers": _headers,
            }
            await self.send(event)

    async def close(self, code: int = 1000, reason: Optional[str] = None) -> None:
        """
        Sends an 'websocket.close' event.
        Args:
            code: Status code.
            reason: Reason for closing the connection

        Returns:
            None
        """
        event: "WebSocketCloseEvent" = {"type": "websocket.close", "code": code, "reason": reason or ""}
        await self.send(event)

    @overload
    async def receive_data(self, mode: "Literal['text']") -> str:
        """Overload of receive_data.

        Args:
            mode: Literal value 'text'

        Returns:
            A string.
        """

    @overload
    async def receive_data(self, mode: "Literal['binary']") -> bytes:
        """Overload of receive_data.

        Args:
            mode: Literal value 'binary'

        Returns:
            A byte-string.
        """

    async def receive_data(self, mode: "Literal['binary', 'text']") -> Union[str, bytes]:
        """Receive an 'websocket.receive' event and returns the data stored on
        it.

        Args:
            mode: The respective event key to use.

        Returns:
            The event's data.
        """
        if self.connection_state == "init":
            await self.accept()
        message = cast("WebSocketReceiveEvent", (await self.receive()))
        if self.connection_state == "disconnect":
            raise RuntimeError()
        return message.get("text") or "" if mode == "text" else message.get("bytes") or b""

    async def receive_text(self) -> str:
        """Receives data as text.

        Returns:
            A string.
        """
        return await self.receive_data(mode="text")

    async def receive_bytes(self) -> bytes:
        """Receives data as bytes.

        Returns:
            A byte-string.
        """
        return await self.receive_data(mode="binary")

    async def receive_json(
        self,
        mode: "Literal['text', 'binary']" = "text",
    ) -> Any:
        """Receives data and loads it into JSON using orson.

        Args:
            mode: Either 'text' or 'binary'.

        Returns:
            An arbitrary value
        """
        data = await self.receive_data(mode=mode)
        return loads(data)

    async def send_data(
        self, data: Union[str, bytes], mode: "Literal['text', 'binary']" = "text", encoding: str = "utf-8"
    ) -> None:
        """Sends a 'websocket.send' event.

        Args:
            data: Data to send.
            mode: The respective event key to use.
            encoding: Encoding to use when converting bytes / str.

        Returns:
            None
        """
        if self.connection_state == "init":
            await self.accept()
        event: "WebSocketSendEvent" = {"type": "websocket.send", "bytes": None, "text": None}
        if mode == "binary":
            event["bytes"] = data if isinstance(data, bytes) else data.encode(encoding)
        else:
            event["text"] = data if isinstance(data, str) else data.decode(encoding)
        await self.send(event)

    @overload
    async def send_text(self, data: bytes, encoding: str = "utf-8") -> None:
        ...

    @overload
    async def send_text(self, data: str) -> None:
        ...

    async def send_text(self, data: Union[str, bytes], encoding: str = "utf-8") -> None:
        """Sends data using the 'text' key of the send event.

        Args:
            data: Data to send
            encoding: Encoding to use for binary data.

        Returns:
            None
        """
        await self.send_data(data=data, mode="text", encoding=encoding)

    @overload
    async def send_bytes(self, data: bytes) -> None:
        ...

    @overload
    async def send_bytes(self, data: str, encoding: str = "utf-8") -> None:
        ...

    async def send_bytes(self, data: Union[str, bytes], encoding: str = "utf-8") -> None:
        """Sends data using the 'bytes' key of the send event.

        Args:
            data: Data to send
            encoding: Encoding to use for binary data.

        Returns:
            None
        """
        await self.send_data(data=data, mode="binary", encoding=encoding)

    async def send_json(
        self,
        data: Any,
        mode: "Literal['text', 'binary']" = "text",
        encoding: str = "utf-8",
        serializer: Serializer = default_serializer,
    ) -> None:
        """Sends data as JSON.

        Args:
            data: A value to serialize.
            mode: Either 'text' or 'binary'.
            encoding: Encoding to use for binary data.
            serializer: A serializer function.
        Returns:
            None
        """
        await self.send_data(
            data=dumps(data, default=serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS),
            mode=mode,
            encoding=encoding,
        )
