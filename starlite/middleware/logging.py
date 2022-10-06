import re
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Set, Type, Union

from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps
from pydantic import BaseModel

from starlite.enums import ScopeType
from starlite.middleware.base import DefineMiddleware, MiddlewareProtocol
from starlite.utils import default_serializer, get_serializer_from_scope
from starlite.utils.extractors import (
    ConnectionDataExtractor,
    RequestExtractorField,
    ResponseDataExtractor,
    ResponseExtractorField,
)

if TYPE_CHECKING:
    from starlite.connection import Request
    from starlite.types import ASGIApp, Logger, Message, Receive, Scope, Send

try:
    from structlog.types import BindableLogger

    structlog_installed = True  # pylint: disable=invalid-name
except ImportError:
    BindableLogger = object  # type: ignore
    structlog_installed = False  # pylint: disable=invalid-name


class LoggingMiddleware(MiddlewareProtocol):
    __slots__ = ("config", "logger", "exclude", "request_extractor", "response_extractor", "is_struct_logger")

    logger: "Logger"

    def __init__(self, app: "ASGIApp", config: "LoggingMiddlewareConfig") -> None:
        """LoggingMiddleware.

        Args:
            app: The 'next' ASGI app to call.
            config: An instance of LoggingMiddlewareConfig.
        """
        self.app = app
        self.is_struct_logger = structlog_installed
        self.config = config
        self.exclude = (
            (re.compile("|".join(config.exclude)) if isinstance(config.exclude, list) else re.compile(config.exclude))
            if config.exclude
            else None
        )
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
        """
        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """

        if scope["type"] == ScopeType.HTTP and not (self.exclude and self.exclude.findall(scope["path"])):
            if not hasattr(self, "logger"):
                self.logger = scope["app"].get_logger(self.config.logger_name)
                self.is_struct_logger = structlog_installed and isinstance(self.logger, BindableLogger)
            if self.config.request_log_fields:
                await self.log_request(scope=scope)
            if self.config.response_log_fields:
                send = self.create_send_wrapper(scope=scope, send=send)
        await self.app(scope, receive, send)

    async def log_request(self, scope: "Scope") -> None:
        """
        Handles extracting the request data and logging the message.
        Args:
            scope: The ASGI connection scope.

        Returns:
            None

        """
        extracted_data = await self.extract_request_data(request=scope["app"].request_class(scope))
        self.log_message(values=extracted_data)

    def log_response(self, scope: "Scope") -> None:
        """Handles extracting the response data and logging the message.

        Args:
            scope: The ASGI connection scope.

        Returns:
            None
        """
        extracted_data = self.extract_response_data(scope=scope)
        self.log_message(values=extracted_data)

    def log_message(self, values: Dict[str, Any]) -> None:
        """

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

    async def extract_request_data(self, request: "Request") -> Dict[str, Any]:
        """Creates a dictionary of values for the message.

        Args:
            request: A [Request][starlite.connection.Request] instance.
        Returns:
            An OrderedDict.
        """

        data: Dict[str, Any] = {"message": self.config.request_log_message}
        serializer = get_serializer_from_scope(request.scope) or default_serializer
        extracted_data = self.request_extractor(connection=request)
        for key in self.config.request_log_fields:
            value = extracted_data.get(key)
            if isawaitable(value):
                value = await value
            if not self.is_struct_logger and isinstance(value, (dict, list, tuple, set)):
                value = dumps(value, default=serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS)
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            data[key] = value
        return data

    def extract_response_data(self, scope: "Scope") -> Dict[str, Any]:
        """
        Extracts data from the response.
        Args:
            scope: The ASGI connection scope.

        Returns:
            An OrderedDict.
        """
        data: Dict[str, Any] = {"message": self.config.response_log_message}
        serializer = get_serializer_from_scope(scope) or default_serializer
        extracted_data = self.response_extractor(
            messages=(
                scope["state"]["http.response.start"],
                scope["state"]["http.response.body"],
            )
        )
        for key in self.config.response_log_fields:
            value = extracted_data.get(key)
            if not self.is_struct_logger and isinstance(value, (dict, list, tuple, set)):
                value = dumps(value, default=serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS)
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            data[key] = value
        return data

    def create_send_wrapper(self, scope: "Scope", send: "Send") -> "Send":
        """Creates a 'send' wrapper, which handles logging response data.

        Args:
            scope: The ASGI connection scope.
            send: The ASGI send function.

        Returns:
            An ASGI send function.
        """

        async def send_wrapper(message: "Message") -> None:
            if message["type"] == "http.response.start":
                scope["state"]["http.response.start"] = message
            elif message["type"] == "http.response.body":
                scope["state"]["http.response.body"] = message
                self.log_response(scope=scope)
            await send(message)

        return send_wrapper


class LoggingMiddlewareConfig(BaseModel):
    exclude: Optional[Union[str, List[str]]] = None
    """
    List of paths to exclude from logging.
    """
    logger_name: str = "starlite"
    """
    Name of the logger to retrieve using `app.get_logger("<name>")`.
    """
    request_cookies_to_obfuscate: Set[str] = {"session"}
    """
    Request cookie keys to obfuscate. Obfuscated values are replaced with '*****'.
    """
    request_headers_to_obfuscate: Set[str] = {"Authorization", "X-API-KEY"}
    """
    Request header keys to obfuscate. Obfuscated values are replaced with '*****'.
    """
    response_cookies_to_obfuscate: Set[str] = {"session"}
    """
    Response cookie keys to obfuscate. Obfuscated values are replaced with '*****'.
    """
    response_headers_to_obfuscate: Set[str] = {"Authorization", "X-API-KEY"}
    """
    Response header keys to obfuscate. Obfuscated values are replaced with '*****'.
    """
    request_log_message: str = "HTTP Request"
    """
    Log message to prepend when logging a request.
    """
    response_log_message: str = "HTTP Response"
    """
    Log message to prepend when logging a response.
    """
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
    """
    Fields to extract and log from the request.

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
    """
    Fields to extract and log from the response. The order of fields in the iterable determines the order of the log message logged out.

    Notes:
        -  The order of fields in the iterable determines the order of the log message logged out.
            Thus, re-arranging the log-message is as simple as changing the iterable.
        -  To turn off logging of responses, use and empty iterable.
    """
    middleware_class: Type[LoggingMiddleware] = LoggingMiddleware
    """
    Middleware class to use. Should be a subclass of [starlite.middleware.LoggingMiddleware].
    """

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one
        of the application layers.

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
