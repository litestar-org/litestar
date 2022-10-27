from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from orjson import OPT_INDENT_2, OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps
from pydantic_openapi_schema.v3_1_0 import OpenAPI
from yaml import dump as dump_yaml

from starlite.datastructures import Cookie, ETag
from starlite.enums import MediaType, OpenAPIMediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.status_codes import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_304_NOT_MODIFIED,
)
from starlite.utils.helpers import get_enum_string_value
from starlite.utils.serialization import default_serializer

if TYPE_CHECKING:
    from typing_extensions import Literal

    from starlite.datastructures import BackgroundTask, BackgroundTasks
    from starlite.types import (
        HTTPResponseBodyEvent,
        HTTPResponseStartEvent,
        Receive,
        ResponseCookies,
        Scope,
        Send,
    )

T = TypeVar("T")


class Response(Generic[T]):
    __slots__ = (
        "status_code",
        "media_type",
        "background",
        "headers",
        "cookies",
        "encoding",
        "body",
        "status_allows_body",
        "is_head_response",
    )

    def __init__(
        self,
        content: T,
        *,
        status_code: int = HTTP_200_OK,
        media_type: Union[MediaType, "OpenAPIMediaType", str] = MediaType.JSON,
        background: Optional[Union["BackgroundTask", "BackgroundTasks"]] = None,
        headers: Optional[Dict[str, Any]] = None,
        cookies: Optional["ResponseCookies"] = None,
        encoding: str = "utf-8",
        is_head_response: bool = False,
    ) -> None:
        """This is the base Starlite HTTP response class, used as the basis for
        all other response classes.

        Args:
            content: A value for the response body that will be rendered into bytes string.
            status_code: An HTTP status code.
            media_type: A value for the response 'Content-Type' header.
            background: A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
                [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
                Defaults to None.
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            cookies: A list of [Cookie][starlite.datastructures.Cookie] instances to be set under the response 'Set-Cookie' header.
            encoding: The encoding to be used for the response headers.
            is_head_response: Whether the response should send only the headers ("head" request) or also the content.
        """
        self.status_code = status_code
        self.media_type = get_enum_string_value(media_type)
        self.background = background
        self.headers = headers or {}
        self.cookies = cookies or []
        self.encoding = encoding
        self.is_head_response = is_head_response
        self.status_allows_body = not (
            self.status_code in {HTTP_204_NO_CONTENT, HTTP_304_NOT_MODIFIED} or self.status_code < HTTP_200_OK
        )
        self.body = self.render(content) if not self.is_head_response else b""

    def set_cookie(
        self,
        key: str,
        value: Optional[str] = None,
        max_age: Optional[int] = None,
        expires: Optional[int] = None,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: 'Literal["lax", "strict", "none"]' = "lax",
    ) -> None:
        """Sets a cookie on the response.

        Args:
            key: Key for the cookie.
            value: Value for the cookie, if none given defaults to empty string.
            max_age: Maximal age of the cookie before its invalidated.
            expires: Expiration date as unix MS timestamp.
            path: Path fragment that must exist in the request url for the cookie to be valid. Defaults to '/'.
            domain: Domain for which the cookie is valid.
            secure: Https is required for the cookie.
            httponly: Forbids javascript to access the cookie via 'Document.cookie'.
            samesite: Controls whether a cookie is sent with cross-site requests. Defaults to 'lax'.

        Returns:
            None.
        """
        self.cookies.append(
            Cookie(
                domain=domain,
                expires=expires,
                httponly=httponly,
                key=key,
                max_age=max_age,
                path=path,
                samesite=samesite,
                secure=secure,
                value=value,
            )
        )

    def set_header(self, key: str, value: str) -> None:
        """Sets a header on the response.

        Args:
            key: Header key.
            value: Header value.

        Returns:
            None.
        """
        self.headers[key] = value

    def set_etag(self, etag: Union[str, "ETag"]) -> None:
        """Sets an etag header.

        Args:
            etag: An etag value.

        Returns:
            None
        """
        self.headers["etag"] = etag.to_header() if isinstance(etag, ETag) else etag

    def delete_cookie(
        self,
        key: str,
        path: str = "/",
        domain: Optional[str] = None,
    ) -> None:
        """Deletes a cookie.

        Args:
            key: Key of the cookie.
            path: Path of the cookie.
            domain: Domain of the cookie.

        Returns:
            None.
        """
        cookie = Cookie(key=key, path=path, domain=domain, expires=0, max_age=0)
        self.cookies = [c for c in self.cookies if c != cookie]
        self.cookies.append(cookie)

    @staticmethod
    def serializer(value: Any) -> Any:
        """Serializer hook for orjson to handle pydantic models.

        Args:
            value: A value to serialize
        Returns:
            A serialized value
        Raises:
            TypeError: if value is not supported
        """
        return default_serializer(value)

    def render(self, content: Any) -> bytes:
        """
        Handles the rendering of content T into a bytes string.
        Args:
            content: A value for the response body that will be rendered into bytes string.

        Returns:
            An encoded bytes string
        """
        if self.status_allows_body:
            if isinstance(content, bytes):
                return content
            if isinstance(content, str):
                return content.encode(self.encoding)
            if self.media_type == MediaType.JSON:
                try:
                    return dumps(content, default=self.serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS)
                except (AttributeError, ValueError, TypeError) as e:
                    raise ImproperlyConfiguredException("Unable to serialize response content") from e
            if isinstance(content, OpenAPI):
                content_dict = content.dict(by_alias=True, exclude_none=True)
                if self.media_type == OpenAPIMediaType.OPENAPI_YAML:
                    return cast("bytes", dump_yaml(content_dict, default_flow_style=False).encode("utf-8"))
                return dumps(content_dict, option=OPT_INDENT_2 | OPT_OMIT_MICROSECONDS)
            if content is None:
                return b""
            raise ImproperlyConfiguredException(
                f"unable to render response body for the given {content} with media_type {self.media_type}"
            )
        if content is not None:
            raise ImproperlyConfiguredException(
                f"status_code {self.status_code} does not support a response body value"
            )
        return b""

    @property
    def content_length(self) -> Optional[int]:
        """

        Returns:
            The content length of the body (e.g. for use in a "Content-Length" header).
            If the response does not have a body, this value is `None`
        """
        if self.status_allows_body:
            return len(self.body)
        return None

    @property
    def encoded_headers(self) -> List[Tuple[bytes, bytes]]:
        """
        Notes:
            - A 'Content-Length' header will be added if appropriate and not provided by the user.

        Returns:
            A list of tuples containing the headers and cookies of the request in a format ready for ASGI transmission.
        """

        if self.media_type.startswith("text/"):
            content_type = f"{self.media_type}; charset={self.encoding}"
        else:
            content_type = self.media_type

        encoded_headers = [
            *((k.lower().encode("latin-1"), str(v).encode("latin-1")) for k, v in self.headers.items()),
            *((b"set-cookie", cookie.to_header(header="").encode("latin-1")) for cookie in self.cookies),
            (b"content-type", content_type.encode("latin-1")),
        ]

        if self.content_length and not any(key == b"content-length" for key, _ in encoded_headers):
            encoded_headers.append((b"content-length", str(self.content_length).encode("latin-1")))
        return encoded_headers

    async def after_response(self) -> None:
        """Executed after the response is sent.

        Returns:
            None
        """
        if self.background is not None:
            await self.background()

    async def start_response(self, send: "Send") -> None:
        """
        Emits the start event of the response. This event includes the headers and status codes.
        Args:
            send: The ASGI send function.

        Returns:
            None
        """
        event: "HTTPResponseStartEvent" = {
            "type": "http.response.start",
            "status": self.status_code,
            "headers": self.encoded_headers,
        }

        await send(event)

    async def send_body(self, send: "Send", receive: "Receive") -> None:  # pylint: disable=unused-argument
        """Emits the response body.

        Args:
            send: The ASGI send function.
            receive: The ASGI receive function.

        Notes:
            - Response subclasses should customize this method if there is a need to customize sending data.

        Returns:
            None
        """
        event: "HTTPResponseBodyEvent" = {"type": "http.response.body", "body": self.body, "more_body": False}
        await send(event)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """The call method of the response is an "ASGIApp".

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        await self.start_response(send=send)

        if self.is_head_response:
            event: "HTTPResponseBodyEvent" = {"type": "http.response.body", "body": b"", "more_body": False}
            await send(event)
        else:
            await self.send_body(send=send, receive=receive)

        await self.after_response()
