from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Set, Type, Union

from pydantic import BaseModel

from starlite.constants import (
    HTTP_RESPONSE_BODY,
    HTTP_RESPONSE_START,
    SCOPE_STATE_RESPONSE_COMPRESSED,
)
from starlite.enums import ScopeType
from starlite.middleware.base import AbstractMiddleware, DefineMiddleware
from starlite.utils import (
    default_serializer,
    get_serializer_from_scope,
    get_starlite_scope_state,
    set_starlite_scope_state,
)
from starlite.utils.extractors import (
    ConnectionDataExtractor,
    RequestExtractorField,
    ResponseDataExtractor,
    ResponseExtractorField,
)
from starlite.utils.serialization import encode_json

if TYPE_CHECKING:
    from starlite.connection import Request
    from starlite.types import (
        ASGIApp,
        Logger,
        Message,
        Receive,
        Scope,
        Send,
        Serializer,
    )

try:
    from structlog.types import BindableLogger

    structlog_installed = True  # pylint: disable=invalid-name
except ImportError:
    BindableLogger = object  # type: ignore
    structlog_installed = False  # pylint: disable=invalid-name


class LoggingMiddleware(AbstractMiddleware):
    """Logging middleware."""

    __slots__ = ("config", "logger", "request_extractor", "response_extractor", "is_struct_logger")

    logger: "Logger"

    def __init__(self, app: "ASGIApp", config: "LoggingMiddlewareConfig") -> None:
        """Initialize `LoggingMiddleware`.

        Args:
            app: The 'next' ASGI app to call.
            config: An instance of LoggingMiddlewareConfig.
        """
        super().__init__(
            app=app, scopes={ScopeType.HTTP}, exclude=config.exclude, exclude_opt_key=config.exclude_opt_key
        )
        self.is_struct_logger = structlog_installed
        self.config = config

        self.request_extractor = ConnectionDataExtractor(
            extract_body="body" in self.config.request_log_fields,
            extract_client="client" in self.config.request_log_fields,
            extract_content_type="content_type" in self.config.request_log_fields,
            extract_cookies="cookies" in self.config.request_log_fields,
            extract_headers="headers" in self.config.request_log_fields,
            extract_method="method" in self.config.request_log_fields,
            extract_path="path" in self.config.request_log_fields,
            extract_path_params="path_params" in self.config.request_log_fields,
            extract_query="query" in self.config.request_log_fields,
            extract_scheme="scheme" in self.config.request_log_fields,
            obfuscate_cookies=self.config.request_cookies_to_obfuscate,
            obfuscate_headers=self.config.request_headers_to_obfuscate,
            parse_body=self.is_struct_logger,
            parse_query=self.is_struct_logger,
        )
        self.response_extractor = ResponseDataExtractor(
            extract_body="body" in self.config.response_log_fields,
            extract_headers="headers" in self.config.response_log_fields,
            extract_status_code="status_code" in self.config.response_log_fields,
            obfuscate_cookies=self.config.response_cookies_to_obfuscate,
            obfuscate_headers=self.config.response_headers_to_obfuscate,
        )

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI callable.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        if not hasattr(self, "logger"):
            self.logger = scope["app"].get_logger(self.config.logger_name)
            self.is_struct_logger = structlog_installed and isinstance(self.logger, BindableLogger)

        if self.config.response_log_fields:
            send = self.create_send_wrapper(scope=scope, send=send)

        if self.config.request_log_fields:
            await self.log_request(scope=scope, receive=receive)

        await self.app(scope, receive, send)

    async def log_request(self, scope: "Scope", receive: "Receive") -> None:
        """Extract request data and log the message.

        Args:
            scope: The ASGI connection scope.
            receive: ASGI receive callable

        Returns:
            None
        """
        extracted_data = await self.extract_request_data(request=scope["app"].request_class(scope, receive=receive))
        self.log_message(values=extracted_data)

    def log_response(self, scope: "Scope") -> None:
        """Extract the response data and log the message.

        Args:
            scope: The ASGI connection scope.

        Returns:
            None
        """
        extracted_data = self.extract_response_data(scope=scope)
        self.log_message(values=extracted_data)

    def log_message(self, values: Dict[str, Any]) -> None:
        """Log a message.

        Args:
            values: Extract values to log.

        Returns:
            None
        """
        message = values.pop("message")
        if self.is_struct_logger:

            self.logger.info(message, **values)
        else:
            self.logger.info(f"{message}: " + ", ".join([f"{key}={value}" for key, value in values.items()]))

    def _serialize_value(self, serializer: Optional["Serializer"], value: Any) -> Any:
        if not self.is_struct_logger and isinstance(value, (dict, list, tuple, set)):
            value = encode_json(value, serializer)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    async def extract_request_data(self, request: "Request") -> Dict[str, Any]:
        """Create a dictionary of values for the message.

        Args:
            request: A [Request][starlite.connection.Request] instance.

        Returns:
            An dict.
        """

        data: Dict[str, Any] = {"message": self.config.request_log_message}
        serializer = get_serializer_from_scope(request.scope)
        extracted_data = self.request_extractor(connection=request)
        for key in self.config.request_log_fields:
            value = extracted_data.get(key)
            if isawaitable(value):
                value = await value
            data[key] = self._serialize_value(serializer, value)
        return data

    def extract_response_data(self, scope: "Scope") -> Dict[str, Any]:
        """Extract data from the response.

        Args:
            scope: The ASGI connection scope.

        Returns:
            An dict.
        """
        data: Dict[str, Any] = {"message": self.config.response_log_message}
        serializer = get_serializer_from_scope(scope) or default_serializer
        extracted_data = self.response_extractor(
            messages=(
                get_starlite_scope_state(scope, HTTP_RESPONSE_START),
                get_starlite_scope_state(scope, HTTP_RESPONSE_BODY),
            ),
        )
        response_body_compressed = get_starlite_scope_state(scope, SCOPE_STATE_RESPONSE_COMPRESSED)
        for key in self.config.response_log_fields:
            value: Any
            value = extracted_data.get(key)
            if key == "body" and response_body_compressed:
                if self.config.include_compressed_body:
                    data[key] = value
                continue
            data[key] = self._serialize_value(serializer, value)
        return data

    def create_send_wrapper(self, scope: "Scope", send: "Send") -> "Send":
        """Create a `send` wrapper, which handles logging response data.

        Args:
            scope: The ASGI connection scope.
            send: The ASGI send function.

        Returns:
            An ASGI send function.
        """

        async def send_wrapper(message: "Message") -> None:
            if message["type"] == HTTP_RESPONSE_START:
                set_starlite_scope_state(scope, HTTP_RESPONSE_START, message)
            elif message["type"] == HTTP_RESPONSE_BODY:
                set_starlite_scope_state(scope, HTTP_RESPONSE_BODY, message)
                self.log_response(scope=scope)
            await send(message)

        return send_wrapper


class LoggingMiddlewareConfig(BaseModel):
    """Configuration for `LoggingMiddleware`"""

    exclude: Optional[Union[str, List[str]]] = None
    """List of paths to exclude from logging."""
    exclude_opt_key: Optional[str] = None
    """An identifier to use on routes to disable logging for a particular route."""
    include_compressed_body: bool = False
    """Include body of compressed response in middleware. If `"body"` not set in.

    [`response_log_fields`][starlite.middleware.logging.LoggingMiddlewareConfig.response_log_fields] this config value
    is ignored.
    """
    logger_name: str = "starlite"
    """Name of the logger to retrieve using `app.get_logger("<name>")`."""
    request_cookies_to_obfuscate: Set[str] = {"session"}
    """Request cookie keys to obfuscate.

    Obfuscated values are replaced with '*****'.
    """
    request_headers_to_obfuscate: Set[str] = {"Authorization", "X-API-KEY"}
    """Request header keys to obfuscate.

    Obfuscated values are replaced with '*****'.
    """
    response_cookies_to_obfuscate: Set[str] = {"session"}
    """Response cookie keys to obfuscate.

    Obfuscated values are replaced with '*****'.
    """
    response_headers_to_obfuscate: Set[str] = {"Authorization", "X-API-KEY"}
    """Response header keys to obfuscate.

    Obfuscated values are replaced with '*****'.
    """
    request_log_message: str = "HTTP Request"
    """Log message to prepend when logging a request."""
    response_log_message: str = "HTTP Response"
    """Log message to prepend when logging a response."""
    request_log_fields: Iterable[RequestExtractorField] = (
        "path",
        "method",
        "content_type",
        "headers",
        "cookies",
        "query",
        "path_params",
        "body",
    )
    """Fields to extract and log from the request.

    Notes:
        -  The order of fields in the iterable determines the order of the log message logged out.
            Thus, re-arranging the log-message is as simple as changing the iterable.
        -  To turn off logging of requests, use and empty iterable.
    """
    response_log_fields: Iterable[ResponseExtractorField] = (
        "status_code",
        "cookies",
        "headers",
        "body",
    )
    """Fields to extract and log from the response. The order of fields in the iterable determines the order of the log
    message logged out.

    Notes:
        -  The order of fields in the iterable determines the order of the log message logged out.
            Thus, re-arranging the log-message is as simple as changing the iterable.
        -  To turn off logging of responses, use and empty iterable.
    """
    middleware_class: Type[LoggingMiddleware] = LoggingMiddleware
    """Middleware class to use.

    Should be a subclass of [starlite.middleware.LoggingMiddleware].
    """

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one of the application layers.

        Examples:
            ```python
            from starlite import Starlite, Request, LoggingConfig, get
            from starlite.middleware.logging import LoggingMiddlewareConfig

            logging_config = LoggingConfig()

            logging_middleware_config = LoggingMiddlewareConfig()


            @get("/")
            def my_handler(request: Request) -> None:
                ...


            app = Starlite(
                route_handlers=[my_handler],
                logging_config=logging_config,
                middleware=[logging_middleware_config.middleware],
            )
            ```

        Returns:
            An instance of DefineMiddleware including 'self' as the config kwarg value.
        """
        return DefineMiddleware(self.middleware_class, config=self)
