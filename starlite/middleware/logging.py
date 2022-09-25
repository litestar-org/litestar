import re
from collections import OrderedDict
from inspect import isawaitable
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Set,
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
    ResponseExtractorField,
)

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Logger, Receive, Scope, Send

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
    log_json: bool = structlog_installed
    log_level: Literal["DEBUG", "INFO"] = "INFO"
    logger_name: str = "starlite"
    obfuscate_cookies: Set[str] = {"session"}
    obfuscate_headers: Set[str] = {"Authorization", "X-API-KEY"}
    request_log_message: str = "HTTP Request"
    response_log_message: str = "HTTP Response"
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
    response_log_field: Iterable[ResponseExtractorField] = (
        "status_code",
        "method",
        "media_type",
        "headers",
        "body",
    )


class LoggingMiddleware(MiddlewareProtocol):
    __slots__ = ("config", "logger", "exclude", "extractor", "is_struct_logger")

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
        self.extractor = ConnectionDataExtractor(
            parse_body=self.config.log_json,
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
            await self.log_request(scope=scope)
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
        self.log_message(message=self.config.request_log_message, scope=scope, values=extracted_data)

    def log_message(self, message: str, scope: "Scope", values: OrderedDict[str, Any]) -> None:
        """

        Args:
            message: Log Message.
            scope: The ASGI connection scope.
            values: Extract values to log.

        Returns:
            None

        """
        if self.is_struct_logger:
            del values["message"]
            self.logger.info(message, **values)
            return

        values["message"] = message
        if self.config.log_json:
            serializer = get_serializer_from_scope(scope) or default_serializer
            self.logger.info(str(dumps(values, default=serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS)))
            return
        self.logger.info(", ".join([f"{key}={value}" for key, value in values.items()]))

    async def extract_request_data(self, request: "Request") -> OrderedDict[str, Any]:
        """Creates a dictionary of values for the message.

        Args:
            request: A [Request][starlite.connection.Request] instance.
        Returns:
            An OrderedDict.
        """

        data: OrderedDict[str, Any] = OrderedDict([("message", "")])
        extracted_data = self.extractor(connection=request)
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
                if isinstance(value, (dict, list, tuple)) and not (self.config.log_json or self.is_struct_logger):
                    serializer = get_serializer_from_scope(request.scope) or default_serializer
                    data[key] = str(
                        dumps(value, default=serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS)
                    )
                else:
                    data[key] = value
        return data
