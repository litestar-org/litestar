from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Generic, Tuple, cast

from starlite.connection.base import (
    ASGIConnection,
    Auth,
    User,
    empty_receive,
    empty_send,
)
from starlite.datastructures.multi_dicts import FormMultiDict
from starlite.enums import RequestEncodingType
from starlite.exceptions import InternalServerException
from starlite.multipart import parse_content_header, parse_multipart_form
from starlite.parsers import parse_url_encoded_form_data
from starlite.types import Empty
from starlite.utils.serialization import decode_json, decode_msgpack

if TYPE_CHECKING:

    from starlite.handlers.http import HTTPRouteHandler  # noqa: F401
    from starlite.types.asgi_types import HTTPScope, Method, Receive, Scope, Send


SERVER_PUSH_HEADERS = {
    "accept",
    "accept-encoding",
    "accept-language",
    "cache-control",
    "user-agent",
}


class Request(Generic[User, Auth], ASGIConnection["HTTPRouteHandler", User, Auth]):
    """The Starlite Request class."""

    __slots__ = ("_json", "_form", "_body", "_msgpack", "_content_type", "is_connected")

    scope: "HTTPScope"
    """The ASGI scope attached to the connection."""
    receive: "Receive"
    """The ASGI receive function."""
    send: "Send"
    """The ASGI send function."""

    def __init__(self, scope: "Scope", receive: "Receive" = empty_receive, send: "Send" = empty_send) -> None:
        """Initialize `Request`.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
        """
        super().__init__(scope, receive, send)
        self.is_connected: bool = True
        self._body: Any = scope.get("_body", Empty)
        self._form: Any = scope.get("_form", Empty)
        self._json: Any = scope.get("_json", Empty)
        self._msgpack: Any = scope.get("_msgpack", Empty)
        self._content_type: Any = scope.get("_content_type", Empty)

    @property
    def method(self) -> "Method":
        """Return the request method.

        Returns:
            The request [Method][starlite.types.Method]
        """
        return self.scope["method"]

    @property
    def content_type(self) -> Tuple[str, Dict[str, str]]:
        """Parse the request's 'Content-Type' header, returning the header value and any options as a dictionary.

        Returns:
            A tuple with the parsed value and a dictionary containing any options send in it.
        """
        if self._content_type is Empty:
            self._content_type = self.scope["_content_type"] = parse_content_header(self.headers.get("Content-Type", ""))  # type: ignore[typeddict-item]
        return cast("Tuple[str, Dict[str, str]]", self._content_type)

    async def json(self) -> Any:
        """Retrieve the json request body from the request.

        Returns:
            An arbitrary value
        """
        if self._json is Empty:
            body = await self.body()
            self._json = self.scope["_json"] = decode_json(body or b"null")  # type: ignore[typeddict-item]
        return self._json

    async def msgpack(self) -> Any:
        """Retrieve the MessagePack request body from the request.

        Returns:
            An arbitrary value
        """
        if self._msgpack is Empty:
            body = await self.body()
            self._msgpack = self.scope["_msgpack"] = decode_msgpack(body or b"\xc0")  # type: ignore[typeddict-item]
        return self._msgpack

    async def stream(self) -> AsyncGenerator[bytes, None]:
        """Return an async generator that streams chunks of bytes.

        Returns:
            An async generator.

        Raises:
            RuntimeError: if the stream is already consumed
        """
        if self._body is Empty:
            if self.is_connected:
                while event := await self.receive():
                    if event["type"] == "http.request":
                        if event["body"]:
                            yield event["body"]
                        if not event.get("more_body", False):
                            break
                    if event["type"] == "http.disconnect":
                        raise InternalServerException("client disconnected prematurely")

                self.is_connected = False
                yield b""
            else:
                raise InternalServerException("stream consumed")
        else:
            yield self._body
            yield b""
            return

    async def body(self) -> bytes:
        """Return the body of the request.

        Returns:
            A byte-string representing the body of the request.
        """
        if self._body is Empty:
            self._body = self.scope["_body"] = b"".join([c async for c in self.stream()])  # type: ignore[typeddict-item]
        return cast("bytes", self._body)

    async def form(self) -> FormMultiDict:
        """Retrieve form data from the request. If the request is either a 'multipart/form-data' or an
        'application/x-www-form- urlencoded', return a FormMultiDict instance populated with the values sent in the
        request, otherwise, an empty instance.

        Returns:
            A FormMultiDict instance
        """
        if self._form is Empty:
            content_type, options = self.content_type
            if content_type == RequestEncodingType.MULTI_PART:
                self._form = self.scope["_form"] = form_values = parse_multipart_form(  # type: ignore[typeddict-item]
                    body=await self.body(), boundary=options.get("boundary", "").encode()
                )
                return FormMultiDict(form_values)
            if content_type == RequestEncodingType.URL_ENCODED:
                self._form = self.scope["_form"] = form_values = parse_url_encoded_form_data(  # type: ignore[typeddict-item]
                    await self.body(),
                )
                return FormMultiDict(form_values)
            return FormMultiDict()
        return FormMultiDict(self._form)

    async def send_push_promise(self, path: str) -> None:
        """Send a push promise.

        This method requires the `http.response.push` extension to be sent from the ASGI server.

        Args:
            path: Path to send the promise to.

        Returns:
            None
        """
        extensions: Dict[str, Dict[Any, Any]] = self.scope.get("extensions") or {}
        if "http.response.push" in extensions:
            raw_headers = []
            for name in SERVER_PUSH_HEADERS:
                for value in self.headers.getall(name, []):
                    raw_headers.append((name.encode("latin-1"), value.encode("latin-1")))
            await self.send({"type": "http.response.push", "path": path, "headers": raw_headers})
