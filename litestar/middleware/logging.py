from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.constants import (
    HTTP_RESPONSE_BODY,
    HTTP_RESPONSE_START,
)
from litestar.data_extractors import (
    ConnectionDataExtractor,
    RequestExtractorField,
    ResponseDataExtractor,
    ResponseExtractorField,
)
from litestar.enums import ScopeType
from litestar.exceptions import HTTPException
from litestar.middleware.base import ASGIMiddleware
from litestar.serialization import encode_json
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from litestar.utils.empty import value_or_default
from litestar.utils.scope import get_serializer_from_scope
from litestar.utils.scope.state import ScopeState

__all__ = ("LoggingMiddleware",)

# Key under which ``LoggingMiddleware`` records, in ``ScopeState.log_context``, the status code of an
# exception it caught. Its presence tells ``extract_response_data()`` that the request ended early, so
# any response message the send wrapper never got to record has to be filled in.
CAUGHT_EXCEPTION_STATUS_CODE = "caught_exception_status_code"


if TYPE_CHECKING:
    import logging
    from collections.abc import Callable, Iterable, Sequence

    from litestar.connection import Request
    from litestar.types import (
        ASGIApp,
        Logger,
        Message,
        Receive,
        Scope,
        Send,
        Serializer,
    )


class LoggingMiddleware(ASGIMiddleware):
    """Logging middleware."""

    scopes = (ScopeType.HTTP,)

    def __init__(
        self,
        logger: logging.Logger | Logger | str | Callable[[], Logger],
        *,
        exclude: str | list[str] | None = None,
        exclude_opt_key: str | None = None,
        include_compressed_body: bool = False,
        request_cookies_to_obfuscate: Iterable[str] = ("session",),
        request_headers_to_obfuscate: Iterable[str] = ("Authorization", "X-API-KEY"),
        response_cookies_to_obfuscate: Iterable[str] = ("session",),
        response_headers_to_obfuscate: Iterable[str] = ("Authorization", "X-API-KEY"),
        request_log_message: str = "HTTP Request",
        response_log_message: str = "HTTP Response",
        request_log_fields: Sequence[RequestExtractorField] = (
            "path",
            "method",
            "content_type",
            "query",
            "path_params",
        ),
        response_log_fields: Sequence[ResponseExtractorField] = ("status_code",),
        parse_body: bool = False,
        parse_query: bool = True,
        log_structured: bool = False,
    ) -> None:
        self.exclude_opt_key = exclude_opt_key
        self.exclude_path_pattern = tuple(exclude) if isinstance(exclude, list) else exclude
        self.include_compressed_body = include_compressed_body
        self.request_cookies_to_obfuscate = frozenset(request_cookies_to_obfuscate)
        self.request_headers_to_obfuscate = frozenset(request_headers_to_obfuscate)
        self.response_cookies_to_obfuscate = frozenset(response_cookies_to_obfuscate)
        self.response_headers_to_obfuscate = frozenset(response_headers_to_obfuscate)
        self.request_log_message = request_log_message
        self.response_log_message = response_log_message
        self.request_log_fields = request_log_fields
        self.response_log_fields = response_log_fields
        self.log_structured = log_structured

        if isinstance(logger, str):
            import logging

            self.logger: Logger | logging.Logger = logging.getLogger(logger)
        elif callable(logger):
            self.logger = logger()
        else:
            self.logger = logger

        self.request_extractor = ConnectionDataExtractor(
            extract_body="body" in self.request_log_fields,
            extract_client="client" in self.request_log_fields,
            extract_content_type="content_type" in self.request_log_fields,
            extract_cookies="cookies" in self.request_log_fields,
            extract_headers="headers" in self.request_log_fields,
            extract_method="method" in self.request_log_fields,
            extract_path="path" in self.request_log_fields,
            extract_path_params="path_params" in self.request_log_fields,
            extract_query="query" in self.request_log_fields,
            extract_scheme="scheme" in self.request_log_fields,
            obfuscate_cookies=self.request_cookies_to_obfuscate,
            obfuscate_headers=self.request_headers_to_obfuscate,
            parse_body=parse_body,
            parse_query=parse_query,
            skip_parse_malformed_body=True,
        )
        self.response_extractor = ResponseDataExtractor(
            extract_body="body" in self.response_log_fields,
            extract_headers="headers" in self.response_log_fields,
            extract_status_code="status_code" in self.response_log_fields,
            obfuscate_cookies=self.response_cookies_to_obfuscate,
            obfuscate_headers=self.response_headers_to_obfuscate,
        )

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        if self.response_log_fields:
            send = self.create_send_wrapper(scope=scope, send=send)

        if self.request_log_fields:
            await self.log_request(scope=scope, receive=receive)

        try:
            await next_app(scope, receive, send)
        except HTTPException as exc:
            # Log response with the correct status code from the exception
            if self.response_log_fields:
                self._log_response_for_caught_exception(scope=scope, status_code=exc.status_code)
            raise
        except Exception:
            # Log response with 500 status for unhandled exceptions
            if self.response_log_fields:
                self._log_response_for_caught_exception(scope=scope, status_code=HTTP_500_INTERNAL_SERVER_ERROR)
            raise

    def _log_response_for_caught_exception(self, scope: Scope, status_code: int) -> None:
        """Log the response for a request that ended in an exception.

        The send wrapper only records response messages that were actually sent, so a request that
        fails early leaves the logging context incomplete. Record the status code the exception maps
        to and let :meth:`extract_response_data` fill in whatever is missing. See #4855.

        Args:
            scope: The ASGI connection scope.
            status_code: The status code the caught exception maps to.

        Returns:
            None
        """
        ScopeState.from_scope(scope).log_context[CAUGHT_EXCEPTION_STATUS_CODE] = status_code
        self.log_response(scope=scope)

    async def log_request(self, scope: Scope, receive: Receive) -> None:
        """Extract request data and log the message.

        Args:
            scope: The ASGI connection scope.
            receive: ASGI receive callable

        Returns:
            None
        """
        extracted_data = await self.extract_request_data(request=scope["litestar_app"].request_class(scope, receive))
        self.log_message(values=extracted_data)

    def log_response(self, scope: Scope) -> None:
        """Extract the response data and log the message.

        Args:
            scope: The ASGI connection scope.

        Returns:
            None
        """
        extracted_data = self.extract_response_data(scope=scope)
        self.log_message(values=extracted_data)

    def log_message(self, values: dict[str, Any]) -> None:
        """Log a message.

        Args:
            values: Extract values to log.

        Returns:
            None
        """
        message = values.pop("message")
        if self.log_structured:
            self.logger.info(message, **values)
        else:
            extra_str = ", ".join(f"{k}={v}" for k, v in values.items())
            self.logger.info(f"{message}: {extra_str}")  # noqa: G004

    def _serialize_value(self, serializer: Serializer | None, value: Any) -> Any:
        if not self.log_structured and isinstance(value, (dict, list, tuple, set)):
            value = encode_json(value, serializer)
        return value.decode("utf-8", errors="backslashreplace") if isinstance(value, bytes) else value

    async def extract_request_data(self, request: Request) -> dict[str, Any]:
        """Create a dictionary of values for the message.

        Args:
            request: A :class:`Request <litestar.connection.Request>` instance.

        Returns:
            An dict.
        """

        data: dict[str, Any] = {"message": self.request_log_message}
        serializer = get_serializer_from_scope(request.scope)

        extracted_data = await self.request_extractor.extract(connection=request, fields=self.request_log_fields)

        for key in self.request_log_fields:
            data[key] = self._serialize_value(serializer, extracted_data.get(key))
        return data

    def extract_response_data(self, scope: Scope) -> dict[str, Any]:
        """Extract data from the response.

        Args:
            scope: The ASGI connection scope.

        Returns:
            An dict.
        """
        data: dict[str, Any] = {"message": self.response_log_message}
        serializer = get_serializer_from_scope(scope)
        connection_state = ScopeState.from_scope(scope)
        caught_exception_status_code = connection_state.log_context.pop(CAUGHT_EXCEPTION_STATUS_CODE, None)
        if caught_exception_status_code is not None:
            # The request ended in an exception, so the send wrapper never recorded the messages the
            # extractor needs. Supply only the ones that are missing, so a response that had already
            # started is logged as it was actually sent rather than being overwritten.
            connection_state.log_context.setdefault(
                HTTP_RESPONSE_START,
                {"type": HTTP_RESPONSE_START, "status": caught_exception_status_code, "headers": []},
            )
            connection_state.log_context.setdefault(HTTP_RESPONSE_BODY, {"type": HTTP_RESPONSE_BODY, "body": b""})
        extracted_data = self.response_extractor(
            messages=(
                # NOTE: we don't pop the start message from the logging context in case
                #   there are multiple body messages to be logged
                connection_state.log_context[HTTP_RESPONSE_START],
                connection_state.log_context.pop(HTTP_RESPONSE_BODY),
            ),
        )
        response_body_compressed = value_or_default(connection_state.response_compressed, False)
        for key in self.response_log_fields:
            value: Any
            value = extracted_data.get(key)
            if key == "body" and response_body_compressed:
                if self.include_compressed_body:
                    data[key] = value
                continue
            data[key] = self._serialize_value(serializer, value)
        return data

    def create_send_wrapper(self, scope: Scope, send: Send) -> Send:
        """Create a ``send`` wrapper, which handles logging response data.

        Args:
            scope: The ASGI connection scope.
            send: The ASGI send function.

        Returns:
            An ASGI send function.
        """
        connection_state = ScopeState.from_scope(scope)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == HTTP_RESPONSE_START:
                connection_state.log_context[HTTP_RESPONSE_START] = message
            elif message["type"] == HTTP_RESPONSE_BODY:
                connection_state.log_context[HTTP_RESPONSE_BODY] = message
                self.log_response(scope=scope)

                if not message.get("more_body"):
                    connection_state.log_context.clear()

            await send(message)

        return send_wrapper
