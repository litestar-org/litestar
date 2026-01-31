from __future__ import annotations

from collections.abc import Collection
from typing import TYPE_CHECKING, Any, Iterable

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
from litestar.middleware.base import ASGIMiddleware
from litestar.serialization import encode_json
from litestar.utils.empty import value_or_default
from litestar.utils.scope import get_serializer_from_scope
from litestar.utils.scope.state import ScopeState

__all__ = (
    "LoggingMiddleware",
    "StructLoggingMiddleware",
)


if TYPE_CHECKING:
    from litestar.connection import Request
    from litestar.types import (
        ASGIApp,
        Message,
        Receive,
        Scope,
        Send,
        Serializer, Logger,
)


class LoggingMiddleware(ASGIMiddleware):
    """Logging middleware."""
    logger: Logger

    scopes = (ScopeType.HTTP,)

    def __init__(
        self,
        *,
        exclude: str | list[str] | None= None,
        exclude_opt_key: str | None = None,
        include_compressed_body: bool = False,
        logger_name: str = "litestar",
        request_cookies_to_obfuscate: Iterable[str] = ("session",),
        request_headers_to_obfuscate: Iterable[str] = ("Authorization", "X-API-KEY"),
        response_cookies_to_obfuscate: Iterable[str] = ("session",),
        response_headers_to_obfuscate: Iterable[str] = ("Authorization", "X-API-KEY"),
        request_log_message: str = "HTTP Request",
        response_log_message: str = "HTTP Response",
        request_log_fields: Collection[RequestExtractorField] = (
            "path",
            "method",
            "content_type",
            "headers",
            "cookies",
            "query",
            "path_params",
            "body",
        ),
        response_log_fields: Collection[ResponseExtractorField]  = (
            "status_code",
            "cookies",
            "headers",
            "body",
        ),
        parse_body: bool = False,
        parse_query: bool = True,
    ) -> None:
        self.exclude_opt_key = exclude_opt_key
        self.exclude_path_pattern = exclude
        self.include_compressed_body = include_compressed_body
        self.logger_name = logger_name
        self.request_cookies_to_obfuscate = frozenset(request_cookies_to_obfuscate)
        self.request_headers_to_obfuscate = frozenset(request_headers_to_obfuscate)
        self.response_cookies_to_obfuscate = frozenset(response_cookies_to_obfuscate)
        self.response_headers_to_obfuscate = frozenset(response_headers_to_obfuscate)
        self.request_log_message = request_log_message
        self.response_log_message = response_log_message
        self.request_log_fields = request_log_fields
        self.response_log_fields = response_log_fields

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
        if not hasattr(self, "logger"):
            self.logger = scope["litestar_app"].get_logger(self.logger_name)

        if self.response_log_fields:
            send = self.create_send_wrapper(scope=scope, send=send)

        if self.request_log_fields:
            await self.log_request(scope=scope, receive=receive)

        await next_app(scope, receive, send)

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
        value_strings = [f"{key}={value}" for key, value in values.items()]
        log_message = f"{message}: {', '.join(value_strings)}"
        self.logger.info(log_message)

    def _serialize_value(self, serializer: Serializer | None, value: Any) -> Any:
        if isinstance(value, (dict, list, tuple, set)):
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


class StructLoggingMiddleware(LoggingMiddleware):
    def log_message(self, values: dict[str, Any]) -> None:
        message = values.pop("message")
        self.logger.info(message, **values)

    def _serialize_value(self, serializer: Serializer | None, value: Any) -> Any:
        return value.decode("utf-8", errors="backslashreplace") if isinstance(value, bytes) else value
