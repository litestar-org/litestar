import re
from collections import OrderedDict
from inspect import isawaitable
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Union,
)

from orjson import OPT_OMIT_MICROSECONDS, OPT_SERIALIZE_NUMPY, dumps
from pydantic import BaseModel

from starlite import (
    ASGIConnection,
    HttpMethod,
    Request,
    RequestEncodingType,
    ScopeType,
    UploadFile,
)
from starlite.middleware.base import MiddlewareProtocol
from starlite.utils import default_serializer, get_serializer_from_scope

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Logger, Method, Receive, Scope, Send

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


class ConnectionDataExtractor:
    __slots__ = ("connection_extractors", "request_extractors", "parse_body", "parse_query")

    def __init__(
        self,
        parse_body: bool = False,
        parse_query: bool = False,
        extract_scheme: bool = True,
        extract_client: bool = True,
        extract_path: bool = True,
        extract_method: bool = True,
        extract_content_type: bool = True,
        extract_headers: bool = True,
        extract_cookies: bool = True,
        extract_query: bool = True,
        extract_path_params: bool = True,
        extract_body: bool = True,
    ):
        """A utility class that extracts data from an.

        [ASGIConnection][starlite.connection.ASGIConnection],

        [Request][starlite.connection.Request] or [WebSocket][starlite.connection.WebSocket] instance.

        Args:
            parse_body: For requests only, whether to parse the body value or return the raw byte string.
            parse_query: Whether to parse query parameters or return the raw byte string.
            extract_scheme: Extract the http scheme.
            extract_client: Extract the client (host, port) mapping.
            extract_path: Extract the path.
            extract_method: For requests only, extract the HTTP method.
            extract_content_type: Extract the content type and any options.
            extract_headers: Extract headers.
            extract_cookies: Extract cookies.
            extract_query: Extract query parameters.
            extract_path_params: Extract path parameters.
            extract_body: For requests only, extract body.
        """
        self.parse_body = parse_body
        self.parse_query = parse_query
        self.connection_extractors: Dict[str, Callable[[ASGIConnection[Any, Any, Any]], Any]] = {}
        self.request_extractors: Dict[str, Callable[[Request[Any, Any]], Any]] = {}
        if extract_scheme:
            self.connection_extractors["scheme"] = self.extract_scheme
        if extract_client:
            self.connection_extractors["client"] = self.extract_client
        if extract_path:
            self.connection_extractors["path"] = self.extract_path
        if extract_headers:
            self.connection_extractors["headers"] = self.extract_headers
        if extract_cookies:
            self.connection_extractors["cookies"] = self.extract_cookies
        if extract_query:
            self.connection_extractors["query"] = self.extract_query
        if extract_path_params:
            self.connection_extractors["path_params"] = self.extract_path_params
        if extract_method:
            self.request_extractors["method"] = self.extract_method
        if extract_content_type:
            self.request_extractors["content_type"] = self.extract_content_type
        if extract_body:
            self.request_extractors["body"] = self.extract_body

    def __call__(self, connection: ASGIConnection[Any, Any, Any]) -> Dict[str, Any]:
        """Extracts data from the connection, returning a dictionary of values.

        Notes:
            - The value for 'body' - if present - is an unresolved Coroutine and as such should be awaited by the receiver.
        Args:
            connection: An ASGI connection or its subclasses.

        Returns:
            A string keyed dictionary of extracted values.
        """

        extractors = (
            {**self.connection_extractors, **self.request_extractors}  # type: ignore
            if isinstance(connection, Request)
            else self.connection_extractors
        )
        return {key: extractor(connection) for key, extractor in extractors.items()}

    @staticmethod
    def extract_scheme(connection: ASGIConnection[Any, Any, Any]) -> str:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            The connection's scope["scheme"] value
        """
        return connection.scope["scheme"]

    @staticmethod
    def extract_client(connection: ASGIConnection[Any, Any, Any]) -> Tuple[str, int]:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            The connection's scope["client"] value or a default value.
        """
        return connection.scope.get("client") or ("", 0)

    @staticmethod
    def extract_path(connection: ASGIConnection[Any, Any, Any]) -> str:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            The connection's scope["path"] value
        """
        return connection.scope["path"]

    @staticmethod
    def extract_headers(connection: ASGIConnection[Any, Any, Any]) -> Dict[str, str]:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            A dictionary with the connection's headers.
        """
        return dict(connection.headers)

    @staticmethod
    def extract_cookies(connection: ASGIConnection[Any, Any, Any]) -> Dict[str, str]:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            A dictionary with the connection's cookies.
        """
        return connection.cookies

    def extract_query(self, connection: ASGIConnection[Any, Any, Any]) -> Any:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            Either a dictionary with the connection's parsed query string or the raw query byte-string.
        """
        return connection.query_params if self.parse_query else connection.scope.get("query_string", b"")

    @staticmethod
    def extract_path_params(connection: ASGIConnection[Any, Any, Any]) -> Dict[str, Any]:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            A dictionary with the connection's path parameters.
        """
        return connection.path_params

    @staticmethod
    def extract_method(request: Request[Any, Any]) -> "Method":
        """

        Args:
            request: A [Request][starlite.connection.Request] instance.

        Returns:
            The request's scope["method"] value.
        """
        return request.scope["method"]

    @staticmethod
    def extract_content_type(request: Request[Any, Any]) -> Tuple[str, Dict[str, str]]:
        """

        Args:
            request: A [Request][starlite.connection.Request] instance.

        Returns:
            A tuple containing the request's parsed 'Content-Type' header.
        """
        return request.content_type

    async def extract_body(self, request: Request[Any, Any]) -> Any:
        """

        Args:
            request: A [Request][starlite.connection.Request] instance.

        Returns:
            Either the parsed request body or the raw byte-string.
        """
        if request.method != HttpMethod.GET:
            if not self.parse_body:
                return await request.body()
            request_encoding_type = request.content_type[0]
            if request_encoding_type == RequestEncodingType.JSON:
                return await request.json()
            form_data = await request.form()
            if request_encoding_type == RequestEncodingType.URL_ENCODED:
                return dict(form_data)
            output: Dict[str, Any] = {}
            for key, value in form_data.multi_items():
                output[key] = repr(value) if isinstance(value, UploadFile) else value
            return output


class LoggingMiddlewareConfig(BaseModel):
    exclude: Optional[Union[str, List[str]]] = None
    log_json: bool = structlog_installed
    log_level: Literal["DEBUG", "INFO"] = "INFO"
    logger_name: str = "starlite"
    obfuscate_cookies: Set[str] = {"session"}
    obfuscate_headers: Set[str] = {"Authorization", "X-API-KEY"}
    request_log_message: str = "HTTP Request"
    response_log_message: str = "HTTP Response"
    request_log_fields: Iterable[str] = (
        "path",
        "method",
        "content_type",
        "headers",
        "cookies",
        "query",
        "path_params",
        "body",
    )
    response_log_field: Iterable[str] = (
        "status_code",
        "method",
        "content_type",
        "headers",
        "cookies",
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
            value = extracted_data[key]
            if key == "data" and request.method != HttpMethod.GET:
                data[key] = await value if isawaitable(value) else value
            elif key in {"headers", "cookies"}:
                obfuscate_keys = self.config.obfuscate_headers if key == "headers" else self.config.obfuscate_cookies
                if obfuscate_keys:
                    value = obfuscate(value, obfuscate_keys)
            if isinstance(value, (dict, list, tuple)) and not (self.config.log_json or self.is_struct_logger):
                serializer = get_serializer_from_scope(request.scope) or default_serializer
                data[key] = str(dumps(value, default=serializer, option=OPT_SERIALIZE_NUMPY | OPT_OMIT_MICROSECONDS))
            else:
                data[key] = value
        return data
