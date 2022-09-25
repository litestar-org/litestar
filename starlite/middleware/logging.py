import re
from collections import OrderedDict
from datetime import date, datetime, time
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Union,
)

from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps
from pydantic import BaseModel

from starlite import HttpMethod, Request, RequestEncodingType, ScopeType
from starlite.middleware.base import MiddlewareProtocol
from starlite.utils import default_serializer, get_serializer_from_scope

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Logger, Receive, Scope, Send

try:
    from structlog._config import BoundLoggerLazyProxy

    structlog_installed = True  # pylint: disable=invalid-name
except ImportError:
    BoundLoggerLazyProxy = object  # type: ignore
    structlog_installed = False  # pylint: disable=invalid-name


def stringify_mapping(mapping: Dict[str, Any]) -> str:
    """Stringifies a dictionary.

    Args:
        mapping: A dictionary of arbitrary values

    Returns:
        A string
    """
    return "; ".join(
        [
            f"{k}: {v}" if not isinstance(v, (date, datetime, time)) else f"{k}: {v.isoformat()}"
            for k, v in mapping.items()
        ]
    )


def extract_and_obfuscate(value: Dict[str, str], field_to_obfuscate: Set[str]) -> Dict[str, str]:
    """
    Args:
        value: A dictionary of strings
        field_to_obfuscate: keys to obfuscate

    Returns:
        A dictionary with obfuscated strings

    """
    return {k: v if k not in field_to_obfuscate else "*" * len(v) for k, v in value}  # type: ignore


def create_extractors(
    request_log_fields: Union[Tuple[str, ...], List[str]],
    obfuscate_headers: Set[str],
    obfuscate_cookies: Set[str],
    log_json: bool,
) -> Dict[str, Callable]:
    """Creates a dictionary mapping keys to extractor functions.

    Args:
        request_log_fields: Fields to include in the log.
        obfuscate_headers: Headers to obfuscate.
        obfuscate_cookies: Cookies to obfuscate.
        log_json: Is the log message json based.

    Returns:
        A dictionary of extractor functions.
    """
    extractors: Dict[str, Callable] = {}
    for key in request_log_fields:
        if key == "path":
            extractors[key] = lambda request: request.scope["path"]
        elif key == "query":
            extractors[key] = lambda request: request.query_params if log_json else request.scope["query_string"]
        elif key == "method":
            extractors[key] = lambda request: request.method
        elif key == "content_type":
            extractors[key] = lambda request: request.content_type[0]
        elif key == "path_params":
            extractors[key] = (
                lambda request: request.path_params if log_json else stringify_mapping(request.path_params)
            )
        elif key == "headers":
            extractors[key] = (
                lambda request: extract_and_obfuscate(dict(request.headers), obfuscate_headers)
                if log_json
                else stringify_mapping(extract_and_obfuscate(dict(request.headers), obfuscate_headers))
            )
        elif key == "cookies":
            extractors[key] = (
                lambda request: extract_and_obfuscate(request.cookies, obfuscate_cookies)
                if log_json
                else stringify_mapping(extract_and_obfuscate(request.cookies, obfuscate_cookies))
            )
    return extractors


class RequestLoggingConfig(BaseModel):
    logger_name: str = "starlite"
    obfuscate_headers: Set[str] = {"Authorization", "X-API-KEY"}
    obfuscate_cookies: Set[str] = {"session"}
    exclude: Optional[Union[str, List[str]]] = None
    request_log_message: str = "HTTP Request"
    response_log_message: str = "HTTP Response"
    log_level: Literal["DEBUG", "INFO"] = "INFO"
    request_log_fields: Union[Tuple[str, ...], List[str]] = (
        "log_message",
        "path",
        "method",
        "content_type",
        "headers",
        "cookies",
        "query",
        "path_params",
        "body",
    )
    log_json: bool = structlog_installed


class RequestLoggingMiddleware(MiddlewareProtocol):
    __slots__ = ("config", "logger", "exclude", "extractors", "is_struct_logger")

    logger: "Logger"

    def __init__(self, app: "ASGIApp", config: "RequestLoggingConfig") -> None:
        """RequestLoggingMiddleware.

        Args:
            app: The 'next' ASGI app to call.
            config: An instance of RequestLoggingConfig.
        """
        self.app = app
        self.is_struct_logger = False
        self.config = config
        self.exclude = (
            (re.compile("|".join(config.exclude)) if isinstance(config.exclude, list) else re.compile(config.exclude))
            if config.exclude
            else None
        )
        self.extractors = create_extractors(
            request_log_fields=config.request_log_fields,
            obfuscate_headers=config.obfuscate_headers,
            obfuscate_cookies=config.obfuscate_cookies,
            log_json=self.config.log_json,
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
                if structlog_installed and isinstance(self.logger, BoundLoggerLazyProxy):
                    self.is_struct_logger = True
            message_dict = await self.create_message_dict(scope=scope)
            if self.is_struct_logger:
                self.logger.info(self.config.request_log_message, **message_dict)
            elif self.config.log_json:
                serializer = get_serializer_from_scope(scope) or default_serializer
                self.logger.info(
                    str(dumps(message_dict, default=serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS))
                )
            else:
                self.logger.info(", ".join([f"{key}={value}" for key, value in message_dict.items()]))
        await self.app(scope, receive, send)

    async def create_message_dict(self, scope: "Scope") -> OrderedDict[str, Any]:
        """
        Creates a dictionary of values for the message.
        Args:
            scope: The ASGI connection scope.

        Returns:
            An OrderedDict.
        """
        request = Request[Any, Any](scope)
        data: OrderedDict[str, Any] = OrderedDict()
        for key in self.config.request_log_fields:
            if key == "msg" and not self.is_struct_logger:
                data[key] = self.config.request_log_message
            elif (
                key == "data"
                and request.method != HttpMethod.GET
                and request.content_type[0] == RequestEncodingType.JSON
            ):
                data[key] = (
                    await request.json() if (self.config.log_json or self.is_struct_logger) else await request.body()
                )
            else:
                extractor = self.extractors[key]
                data[key] = extractor(request)
        return data
