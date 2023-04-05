from __future__ import annotations

from functools import partial
from itertools import chain
from typing import TYPE_CHECKING, Any, Generic, Literal, Mapping, TypeVar, overload

from litestar.datastructures.cookie import Cookie
from litestar.datastructures.headers import ETag
from litestar.enums import MediaType, OpenAPIMediaType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.serialization import DEFAULT_TYPE_ENCODERS, default_serializer, encode_json, encode_msgpack
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_304_NOT_MODIFIED
from litestar.utils.helpers import get_enum_string_value

__all__ = ("Response",)


if TYPE_CHECKING:
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.types import (
        HTTPResponseBodyEvent,
        HTTPResponseStartEvent,
        Receive,
        ResponseCookies,
        ResponseHeaders,
        Scope,
        Send,
        Serializer,
        TypeEncodersMap,
    )

T = TypeVar("T")


class Response(Generic[T]):
    """Base Litestar HTTP response class, used as the basis for all other response classes."""

    __slots__ = (
        "background",
        "body",
        "cookies",
        "encoding",
        "headers",
        "is_head_response",
        "is_text_response",
        "media_type",
        "status_allows_body",
        "status_code",
        "raw_headers",
        "_enc_hook",
    )

    type_encoders: TypeEncodersMap | None = None

    def __init__(
        self,
        content: T,
        *,
        status_code: int = HTTP_200_OK,
        media_type: MediaType | OpenAPIMediaType | str = MediaType.JSON,
        background: BackgroundTask | BackgroundTasks | None = None,
        headers: ResponseHeaders | None = None,
        cookies: ResponseCookies | None = None,
        encoding: str = "utf-8",
        is_head_response: bool = False,
        type_encoders: TypeEncodersMap | None = None,
    ) -> None:
        """Initialize the response.

        Args:
            content: A value for the response body that will be rendered into bytes string.
            status_code: An HTTP status code.
            media_type: A value for the response ``Content-Type`` header.
            background: A :class:`BackgroundTask <.background_tasks.BackgroundTask>` instance or
                :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` to execute after the response is finished.
                Defaults to ``None``.
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            cookies: A list of :class:`Cookie <.datastructures.Cookie>` instances to be set under the response
                ``Set-Cookie`` header.
            encoding: The encoding to be used for the response headers.
            is_head_response: Whether the response should send only the headers ("head" request) or also the content.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
        """
        self.background = background
        self.cookies: list[Cookie] = (
            [Cookie(key=key, value=value) for key, value in cookies.items()]
            if isinstance(cookies, Mapping)
            else list(cookies or [])
        )
        self.encoding = encoding
        self.headers: dict[str, Any] = (
            dict(headers) if isinstance(headers, Mapping) else {h.name: h.value for h in headers or {}}
        )
        self.is_head_response = is_head_response
        self.media_type = get_enum_string_value(media_type)
        self.status_allows_body = not (
            status_code in {HTTP_204_NO_CONTENT, HTTP_304_NOT_MODIFIED} or status_code < HTTP_200_OK
        )
        self.status_code = status_code
        self._enc_hook = self.get_serializer(type_encoders)

        if not self.status_allows_body or is_head_response:
            if content:
                raise ImproperlyConfiguredException(
                    "response content is not supported for HEAD responses and responses with a status code "
                    "that does not allow content (304, 204, < 200)"
                )
            self.body = b""
        else:
            self.body = content if isinstance(content, bytes) else self.render(content)

        self.headers.setdefault(
            "content-type",
            f"{self.media_type}; charset={self.encoding}" if self.media_type.startswith("text/") else self.media_type,
        )
        self.raw_headers: list[tuple[bytes, bytes]] = []

    @classmethod
    def get_serializer(cls, type_encoders: TypeEncodersMap | None = None) -> Serializer:
        """Get the serializer for this response class."""

        type_encoders = {**(cls.type_encoders or {}), **(type_encoders or {})}
        if type_encoders:
            return partial(default_serializer, type_encoders={**DEFAULT_TYPE_ENCODERS, **type_encoders})

        return default_serializer

    @overload
    def set_cookie(self, /, cookie: Cookie) -> None:
        ...

    @overload
    def set_cookie(
        self,
        key: str,
        value: str | None = None,
        max_age: int | None = None,
        expires: int | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] = "lax",
    ) -> None:
        ...

    def set_cookie(  # type: ignore[misc]
        self,
        key: str | Cookie,
        value: str | None = None,
        max_age: int | None = None,
        expires: int | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] = "lax",
    ) -> None:
        """Set a cookie on the response. If passed a :class:`Cookie <.datastructures.Cookie>` instance, keyword
        arguments will be ignored.

        Args:
            key: Key for the cookie or a :class:`Cookie <.datastructures.Cookie>` instance.
            value: Value for the cookie, if none given defaults to empty string.
            max_age: Maximal age of the cookie before its invalidated.
            expires: Expiration date as unix MS timestamp.
            path: Path fragment that must exist in the request url for the cookie to be valid. Defaults to ``/``.
            domain: Domain for which the cookie is valid.
            secure: Https is required for the cookie.
            httponly: Forbids javascript to access the cookie via ``document.cookie``.
            samesite: Controls whether a cookie is sent with cross-site requests. Defaults to ``lax``.

        Returns:
            None.
        """
        if not isinstance(key, Cookie):
            key = Cookie(
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
        self.cookies.append(key)

    def set_header(self, key: str, value: str) -> None:
        """Set a header on the response.

        Args:
            key: Header key.
            value: Header value.

        Returns:
            None.
        """
        self.headers[key] = value

    def set_etag(self, etag: str | ETag) -> None:
        """Set an etag header.

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
        domain: str | None = None,
    ) -> None:
        """Delete a cookie.

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

    def render(self, content: Any) -> bytes:
        """Handle the rendering of content into a bytes string.

        Args:
            content: A value for the response body that will be rendered into bytes string.

        Returns:
            An encoded bytes string
        """
        try:
            if self.media_type.startswith("text/"):
                if not content:
                    return b""

                return content.encode(self.encoding)  # type: ignore

            if self.media_type == MediaType.MESSAGEPACK:
                return encode_msgpack(content, self._enc_hook)

            return encode_json(content, self._enc_hook)
        except (AttributeError, ValueError, TypeError) as e:
            raise ImproperlyConfiguredException("Unable to serialize response content") from e

    @property
    def content_length(self) -> int:
        """Content length of the response if applicable.

        Returns:
            The content length of the body (e.g. for use in a ``Content-Length`` header).
            If the response does not have a body, this value is ``None``
        """
        if self.status_allows_body:
            return len(self.body)
        return 0

    def encode_headers(self) -> list[tuple[bytes, bytes]]:
        """Encode the response headers as a list of byte tuples.

        Notes:
            - A ``Content-Length`` header will be added if appropriate and not provided by the user.

        Returns:
            A list of tuples containing the headers and cookies of the request in a format ready for ASGI transmission.
        """

        return list(
            chain(
                ((k.lower().encode("latin-1"), str(v).encode("latin-1")) for k, v in self.headers.items()),
                (cookie.to_encoded_header() for cookie in self.cookies),
                self.raw_headers,
            )
        )

    async def after_response(self) -> None:
        """Execute after the response is sent.

        Returns:
            None
        """
        if self.background is not None:
            await self.background()

    async def start_response(self, send: "Send") -> None:
        """Emit the start event of the response. This event includes the headers and status codes.

        Args:
            send: The ASGI send function.

        Returns:
            None
        """

        encoded_headers = self.encode_headers()

        content_length = self.content_length
        if "content-length" not in self.headers and content_length:
            encoded_headers.append((b"content-length", str(content_length).encode("latin-1")))

        event: HTTPResponseStartEvent = {
            "type": "http.response.start",
            "status": self.status_code,
            "headers": encoded_headers,
        }

        await send(event)

    async def send_body(self, send: "Send", receive: "Receive") -> None:
        """Emit the response body.

        Args:
            send: The ASGI send function.
            receive: The ASGI receive function.

        Notes:
            - Response subclasses should customize this method if there is a need to customize sending data.

        Returns:
            None
        """
        event: HTTPResponseBodyEvent = {"type": "http.response.body", "body": self.body, "more_body": False}
        await send(event)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI callable of the ``Response``.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        await self.start_response(send=send)

        if self.is_head_response:
            event: HTTPResponseBodyEvent = {"type": "http.response.body", "body": b"", "more_body": False}
            await send(event)
        else:
            await self.send_body(send=send, receive=receive)

        await self.after_response()
