from __future__ import annotations

import math
from typing import TYPE_CHECKING, cast

from litestar.datastructures import Headers
from litestar.exceptions import ClientException
from litestar.exceptions.http_exceptions import RequestEntityTooLarge
from litestar.middleware.base import ASGIMiddleware

if TYPE_CHECKING:
    from litestar.types import ASGIApp, HTTPReceiveMessage, Receive, Scope, Send


def _get_content_length(headers: Headers) -> int | None:
    content_length_header = headers.get("content-length")
    try:
        return int(content_length_header) if content_length_header is not None else None
    except ValueError:
        raise ClientException(f"Invalid content-length: {content_length_header!r}") from None


class RequestMaxBodySizeMiddleware(ASGIMiddleware):
    def __init__(self, max_content_length: int | None) -> None:
        self.max_content_length = max_content_length

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        headers = Headers.from_scope(scope)
        announced_content_length = _get_content_length(headers)
        max_content_length = self.max_content_length or math.inf
        # setting this to 'math.inf' as a micro-optimisation; Comparing against a
        # float is slightly faster than checking if a value is 'None' and then
        # comparing it to an int. since we expect a limit to be set most of the
        # time, this is a bit more efficient

        # if the 'content-length' header is set, and exceeds the limit, we can bail
        # out early before reading anything
        if announced_content_length is not None and announced_content_length > max_content_length:
            raise RequestEntityTooLarge

        total_bytes_streamed: int = 0

        async def wrapped_receive() -> HTTPReceiveMessage:
            nonlocal total_bytes_streamed
            event = cast("HTTPReceiveMessage", await receive())
            if event["type"] == "http.request":
                body = event["body"]
                if body:
                    total_bytes_streamed += len(body)

                    # if a 'content-length' header was set, check if we have
                    # received more bytes than specified. in most cases this should
                    # be caught before it hits the application layer and an ASGI
                    # server (e.g. uvicorn) will not allow this, but since it's not
                    # forbidden according to the HTTP or ASGI spec, we err on the
                    # side of caution and still perform this check.
                    #
                    # uvicorn documented behaviour for this case:
                    # https://github.com/encode/uvicorn/blob/fe3910083e3990695bc19c2ef671dd447262ae18/docs/server-behavior.md?plain=1#L11
                    if announced_content_length:
                        if total_bytes_streamed > announced_content_length:
                            raise ClientException("Malformed request")

                    # we don't have a 'content-length' header, likely a chunked
                    # transfer. we don't really care and simply check if we have
                    # received more bytes than allowed
                    elif total_bytes_streamed > max_content_length:
                        raise RequestEntityTooLarge
            return event

        await next_app(scope, wrapped_receive, send)
