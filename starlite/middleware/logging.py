import re
from collections import OrderedDict
from inspect import isawaitable
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps
from pydantic import BaseModel

from starlite import HttpMethod, Request, ScopeType
from starlite.middleware.base import MiddlewareProtocol
from starlite.utils import default_serializer, get_serializer_from_scope
from starlite.utils.extractors import (
    ConnectionDataExtractor,
    RequestExtractorField,
    ResponseDataExtractor,
    ResponseExtractorField,
)

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Logger, Message, Receive, Scope, Send
    from starlite.types.asgi_types import HTTPResponseBodyEvent, HTTPResponseStartEvent

try:
    from structlog._config import BoundLoggerLazyProxy

    structlog_installed = True  # pylint: disable=invalid-name
except ImportError:
    BoundLoggerLazyProxy = object  # type: ignore
    structlog_installed = False  # pylint: disable=invalid-name


def obfuscate(value: Dict[str, str], fields_to_obfuscate: Set[str]) -> Dict[str, str]:
    """
    Args:
        value: A dictionary of strings
        fields_to_obfuscate: keys to obfuscate

    Returns:
        A dictionary with obfuscated strings

    """
    return {k: v if k not in fields_to_obfuscate else "*" * len(v) for k, v in value}  # type: ignore


class LoggingMiddlewareConfig(BaseModel):
    exclude: Optional[Union[str, List[str]]] = None
    """
    List of paths to exclude from logging.
    """
    logger_name: str = "starlite"
    """
    Name of the logger to retrieve using `app.get_logger("<name>")`.
    """
    obfuscate_cookies: Set[str] = {"session"}
    """
    Cookie keys to obfuscate. Obfuscated values are replaced with '*****' (max 10 char length).
    """
    obfuscate_headers: Set[str] = {"Authorization", "X-API-KEY"}
    """
    Header keys to obfuscate. Obfuscated values are replaced with '*****' (max 10 char length).
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
    response_log_fields: Iterable[ResponseExtractorField] = (
        "status_code",
        "method",
        "media_type",
        "headers",
        "body",
    )


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
            parse_body=self.is_struct_logger,
            extract_scheme="scheme" in self.config.request_log_fields,
            extract_client="client" in self.config.request_log_fields,
            extract_path="path" in self.config.request_log_fields,
            extract_method="method" in self.config.request_log_fields,
            extract_content_type="content_type" in self.config.request_log_fields,
            extract_headers="headers" in self.config.request_log_fields,
            extract_cookies="cookies" in self.config.request_log_fields,
            extract_query="query" in self.config.request_log_fields,
            extract_path_params="path_params" in self.config.request_log_fields,
            extract_body="body" in self.config.request_log_fields,
        )
        self.response_extractor = ResponseDataExtractor(
            parse_headers=True,
            extract_body="body" in self.config.response_log_fields,
            extract_status_code="status_code" in self.config.response_log_fields,
            extract_headers="headers" in self.config.response_log_fields,
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

        if scope["type"] == ScopeType.HTTP and (not self.exclude or not self.exclude.findall(scope["path"])):
            if not hasattr(self, "logger"):
                self.logger = scope["app"].get_logger(self.config.logger_name)
                self.is_struct_logger = structlog_installed and isinstance(self.logger, BoundLoggerLazyProxy)
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
        extracted_data = await self.extract_request_data(request=Request[Any, Any](scope))
        self.log_message(values=extracted_data)

    def log_response(self, scope: "Scope") -> None:
        """

        Args:
            scope: The ASGI connection scope.

        Returns:
            None
        """
        extracted_data = self.extract_response_data(
            messages=(scope["state"]["http.response.start"], scope["state"]["http.response.body"])
        )
        self.log_message(values=extracted_data)

    def log_message(self, values: OrderedDict[str, Any]) -> None:
        """

        Args:
            values: Extract values to log.

        Returns:
            None

        """
        if self.is_struct_logger:
            message = values.pop("message")
            self.logger.info(message, **values)
        else:
            self.logger.info(", ".join([f"{key}={value}" for key, value in values.items()]))

    async def extract_request_data(self, request: "Request") -> OrderedDict[str, Any]:
        """Creates a dictionary of values for the message.

        Args:
            request: A [Request][starlite.connection.Request] instance.
        Returns:
            An OrderedDict.
        """

        data: OrderedDict[str, Any] = OrderedDict([("message", self.config.request_log_message)])
        extracted_data = self.request_extractor(connection=request)
        for key in self.config.request_log_fields:
            if key in extracted_data:
                value = extracted_data[key]  # pyright: ignore
                if key == "body" and request.method != HttpMethod.GET:
                    data[key] = await value if isawaitable(value) else value
                elif key in {"headers", "cookies"}:
                    obfuscate_keys = (
                        self.config.obfuscate_headers if key == "headers" else self.config.obfuscate_cookies
                    )
                    if obfuscate_keys:
                        value = obfuscate(cast("Dict[str, str]", value), obfuscate_keys)
                if isinstance(value, (dict, list, tuple)) and not self.is_struct_logger:
                    serializer = get_serializer_from_scope(request.scope) or default_serializer
                    data[key] = str(
                        dumps(value, default=serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS)
                    )
                else:
                    data[key] = value
        return data

    def extract_response_data(
        self, messages: Tuple["HTTPResponseStartEvent", "HTTPResponseBodyEvent"]
    ) -> OrderedDict[str, Any]:
        """
        Extracts data from the response.
        Args:
            messages: A tuple of ASGI messages.

        Returns:
            An OrderedDict.
        """
        data: OrderedDict[str, Any] = OrderedDict([("message", self.config.response_log_message)])
        extracted_data = self.response_extractor(messages=messages)

        for key in self.config.response_log_fields:
            data[key] = extracted_data.get(key)
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
