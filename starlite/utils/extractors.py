from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

from starlette.requests import cookie_parser
from typing_extensions import Literal, TypedDict

from starlite.connection import Request
from starlite.datastructures.upload_file import UploadFile
from starlite.enums import HttpMethod, RequestEncodingType

if TYPE_CHECKING:
    from starlite.connection import ASGIConnection
    from starlite.types import Method
    from starlite.types.asgi_types import HTTPResponseBodyEvent, HTTPResponseStartEvent


def obfuscate(values: Dict[str, Any], fields_to_obfuscate: Set[str]) -> Dict[str, Any]:
    """
    Args:
        values: A dictionary of strings
        fields_to_obfuscate: keys to obfuscate

    Returns:
        A dictionary with obfuscated strings

    """

    for key in values:
        if key.lower() in fields_to_obfuscate:
            values[key] = "*****"
    return values


RequestExtractorField = Literal[
    "path", "method", "content_type", "headers", "cookies", "query", "path_params", "body", "scheme", "client"
]

ResponseExtractorField = Literal["status_code", "method", "headers", "body", "cookies"]


class ExtractedRequestData(TypedDict, total=False):
    body: Coroutine
    client: Tuple[str, int]
    content_type: Tuple[str, Dict[str, str]]
    cookies: Dict[str, str]
    headers: Dict[str, str]
    method: "Method"
    path: str
    path_params: Dict[str, Any]
    query: Union[bytes, Dict[str, Any]]
    scheme: str


class ConnectionDataExtractor:
    __slots__ = (
        "connection_extractors",
        "request_extractors",
        "parse_body",
        "parse_query",
        "obfuscate_headers",
        "obfuscate_cookies",
    )

    def __init__(
        self,
        extract_body: bool = True,
        extract_client: bool = True,
        extract_content_type: bool = True,
        extract_cookies: bool = True,
        extract_headers: bool = True,
        extract_method: bool = True,
        extract_path: bool = True,
        extract_path_params: bool = True,
        extract_query: bool = True,
        extract_scheme: bool = True,
        obfuscate_cookies: Optional[Set[str]] = None,
        obfuscate_headers: Optional[Set[str]] = None,
        parse_body: bool = False,
        parse_query: bool = False,
    ):
        """A utility class that extracts data from an.

        [ASGIConnection][starlite.connection.ASGIConnection],

        [Request][starlite.connection.Request] or [WebSocket][starlite.connection.WebSocket] instance.

        Args:
            extract_body: Whether to extract body, (for requests only).
            extract_client: Whether to extract the client (host, port) mapping.
            extract_content_type: Whether to extract the content type and any options.
            extract_cookies: Whether to extract cookies.
            extract_headers: Whether to extract headers.
            extract_method: Whether to extract the HTTP method, (for requests only).
            extract_path: Whether to extract the path.
            extract_path_params: Whether to extract path parameters.
            extract_query: Whether to extract query parameters.
            extract_scheme: Whether to extract the http scheme.
            obfuscate_headers: headers keys to obfuscate. Obfuscated values are replaced with '*****'.
            obfuscate_cookies: cookie keys to obfuscate. Obfuscated values are replaced with '*****'.
            parse_body: Whether to parse the body value or return the raw byte string, (for requests only).
            parse_query: Whether to parse query parameters or return the raw byte string.
        """
        self.parse_body = parse_body
        self.parse_query = parse_query
        self.obfuscate_headers = {h.lower() for h in (obfuscate_headers or set())}
        self.obfuscate_cookies = {c.lower() for c in (obfuscate_cookies or set())}
        self.connection_extractors: Dict[str, Callable[["ASGIConnection[Any, Any, Any]"], Any]] = {}
        self.request_extractors: Dict[RequestExtractorField, Callable[["Request[Any, Any]"], Any]] = {}
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

    def __call__(self, connection: "ASGIConnection[Any, Any, Any]") -> ExtractedRequestData:
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
        return cast("ExtractedRequestData", {key: extractor(connection) for key, extractor in extractors.items()})

    @staticmethod
    def extract_scheme(connection: "ASGIConnection[Any, Any, Any]") -> str:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            The connection's scope["scheme"] value
        """
        return connection.scope["scheme"]

    @staticmethod
    def extract_client(connection: "ASGIConnection[Any, Any, Any]") -> Tuple[str, int]:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            The connection's scope["client"] value or a default value.
        """
        return connection.scope.get("client") or ("", 0)

    @staticmethod
    def extract_path(connection: "ASGIConnection[Any, Any, Any]") -> str:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            The connection's scope["path"] value
        """
        return connection.scope["path"]

    def extract_headers(self, connection: "ASGIConnection[Any, Any, Any]") -> Dict[str, str]:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            A dictionary with the connection's headers.
        """
        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in connection.scope["headers"]}
        return obfuscate(headers, self.obfuscate_headers) if self.obfuscate_headers else headers

    def extract_cookies(self, connection: "ASGIConnection[Any, Any, Any]") -> Dict[str, str]:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            A dictionary with the connection's cookies.
        """
        return obfuscate(connection.cookies, self.obfuscate_cookies) if self.obfuscate_cookies else connection.cookies

    def extract_query(self, connection: "ASGIConnection[Any, Any, Any]") -> Any:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            Either a dictionary with the connection's parsed query string or the raw query byte-string.
        """
        return connection.query_params if self.parse_query else connection.scope.get("query_string", b"")

    @staticmethod
    def extract_path_params(connection: "ASGIConnection[Any, Any, Any]") -> Dict[str, Any]:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            A dictionary with the connection's path parameters.
        """
        return connection.path_params

    @staticmethod
    def extract_method(request: "Request[Any, Any]") -> "Method":
        """

        Args:
            request: A [Request][starlite.connection.Request] instance.

        Returns:
            The request's scope["method"] value.
        """
        return request.scope["method"]

    @staticmethod
    def extract_content_type(request: "Request[Any, Any]") -> Tuple[str, Dict[str, str]]:
        """

        Args:
            request: A [Request][starlite.connection.Request] instance.

        Returns:
            A tuple containing the request's parsed 'Content-Type' header.
        """
        return request.content_type

    async def extract_body(self, request: "Request[Any, Any]") -> Any:
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
            return {
                key: repr(value) if isinstance(value, UploadFile) else value for key, value in form_data.multi_items()
            }


class ExtractedResponseData(TypedDict, total=False):
    body: bytes
    status_code: int
    headers: Dict[str, str]
    cookies: Dict[str, str]


class ResponseDataExtractor:
    __slots__ = ("extractors", "parse_headers", "obfuscate_headers", "obfuscate_cookies")

    def __init__(
        self,
        extract_body: bool = True,
        extract_cookies: bool = True,
        extract_headers: bool = True,
        extract_status_code: bool = True,
        obfuscate_cookies: Optional[Set[str]] = None,
        obfuscate_headers: Optional[Set[str]] = None,
    ):
        """A utility class that extracts data from response messages.

        Args:
            extract_body: Whether to extract the body.
            extract_cookies: Whether to extract the cookies.
            extract_headers: Whether to extract the headers.
            extract_status_code: Whether to extract the status code.
            obfuscate_cookies: cookie keys to obfuscate. Obfuscated values are replaced with '*****'.
            obfuscate_headers: headers keys to obfuscate. Obfuscated values are replaced with '*****'.
        """
        self.obfuscate_headers = {h.lower() for h in (obfuscate_headers or set())}
        self.obfuscate_cookies = {c.lower() for c in (obfuscate_cookies or set())}
        self.extractors: Dict[
            ResponseExtractorField, Callable[[Tuple["HTTPResponseStartEvent", "HTTPResponseBodyEvent"]], Any]
        ] = {}
        if extract_body:
            self.extractors["body"] = self.extract_response_body
        if extract_status_code:
            self.extractors["status_code"] = self.extract_status_code
        if extract_headers:
            self.extractors["headers"] = self.extract_headers
        if extract_cookies:
            self.extractors["cookies"] = self.extract_cookies

    def __call__(self, messages: Tuple["HTTPResponseStartEvent", "HTTPResponseBodyEvent"]) -> ExtractedResponseData:
        """Extracts data from the response, returning a dictionary of values.

        Args:
            messages: A tuple containing
                [HTTPResponseStartEvent][starlite.types.asgi_types.HTTPResponseStartEvent]
                and [HTTPResponseBodyEvent][starlite.types.asgi_types.HTTPResponseBodyEvent].
        Returns:
            A string keyed dictionary of extracted values.
        """
        return cast("ExtractedResponseData", {key: extractor(messages) for key, extractor in self.extractors.items()})

    @staticmethod
    def extract_response_body(messages: Tuple["HTTPResponseStartEvent", "HTTPResponseBodyEvent"]) -> bytes:
        """

        Args:
            messages: A tuple containing
                [HTTPResponseStartEvent][starlite.types.asgi_types.HTTPResponseStartEvent]
                and [HTTPResponseBodyEvent][starlite.types.asgi_types.HTTPResponseBodyEvent].
        Returns:
            The Response's body as a byte-string.
        """
        return messages[1]["body"]

    @staticmethod
    def extract_status_code(messages: Tuple["HTTPResponseStartEvent", "HTTPResponseBodyEvent"]) -> int:
        """

        Args:
            messages: A tuple containing
                [HTTPResponseStartEvent][starlite.types.asgi_types.HTTPResponseStartEvent]
                and [HTTPResponseBodyEvent][starlite.types.asgi_types.HTTPResponseBodyEvent].
        Returns:
            The Response's status-code.
        """
        return messages[0]["status"]

    def extract_headers(self, messages: Tuple["HTTPResponseStartEvent", "HTTPResponseBodyEvent"]) -> Dict[str, str]:
        """

        Args:
            messages: A tuple containing
                [HTTPResponseStartEvent][starlite.types.asgi_types.HTTPResponseStartEvent]
                and [HTTPResponseBodyEvent][starlite.types.asgi_types.HTTPResponseBodyEvent].
        Returns:
            The Response's headers dict.
        """
        headers = {
            key.decode("latin-1"): value.decode("latin-1")
            for key, value in filter(lambda x: x[0].lower() != b"set-cookie", messages[0]["headers"])
        }
        return (
            obfuscate(
                headers,
                self.obfuscate_headers,
            )
            if self.obfuscate_headers
            else headers
        )

    def extract_cookies(self, messages: Tuple["HTTPResponseStartEvent", "HTTPResponseBodyEvent"]) -> Dict[str, str]:
        """

        Args:
            messages: A tuple containing
                [HTTPResponseStartEvent][starlite.types.asgi_types.HTTPResponseStartEvent]
                and [HTTPResponseBodyEvent][starlite.types.asgi_types.HTTPResponseBodyEvent].

        Returns:
            The Response's cookies dict.
        """
        cookie_string = ";".join(
            list(
                map(
                    lambda x: x[1].decode("latin-1"),
                    filter(lambda x: x[0].lower() == b"set-cookie", messages[0]["headers"]),
                )
            )
        )
        if cookie_string:
            parsed_cookies = cookie_parser(cookie_string)
            return obfuscate(parsed_cookies, self.obfuscate_cookies) if self.obfuscate_cookies else parsed_cookies
        return {}
