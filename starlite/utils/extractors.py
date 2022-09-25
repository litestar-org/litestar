from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    Literal,
    Tuple,
    Union,
    cast,
)

from typing_extensions import TypedDict

from starlite.connection import Request
from starlite.datastructures import UploadFile
from starlite.enums import HttpMethod, MediaType, RequestEncodingType

if TYPE_CHECKING:
    from starlette.responses import Response as StarletteResponse

    from starlite.connection import ASGIConnection
    from starlite.types import Method

RequestExtractorField = Literal[
    "path", "method", "content_type", "headers", "cookies", "query", "path_params", "body", "scheme", "client"
]

ResponseExtractorField = Literal["status_code", "method", "media_type", "headers", "body"]


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
    __slots__ = ("connection_extractors", "request_extractors", "parse_body", "parse_query")

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
        parse_body: bool = False,
        parse_query: bool = False,
    ):
        """A utility class that extracts data from an.

        [ASGIConnection][starlite.connection.ASGIConnection],

        [Request][starlite.connection.Request] or [WebSocket][starlite.connection.WebSocket] instance.

        Args:
            extract_body: For requests only, extract body.
            extract_client: Extract the client (host, port) mapping.
            extract_content_type: Extract the content type and any options.
            extract_cookies: Extract cookies.
            extract_headers: Extract headers.
            extract_method: For requests only, extract the HTTP method.
            extract_path: Extract the path.
            extract_path_params: Extract path parameters.
            extract_query: Extract query parameters.
            extract_scheme: Extract the http scheme.
            parse_body: For requests only, whether to parse the body value or return the raw byte string.
            parse_query: Whether to parse query parameters or return the raw byte string.
        """
        self.parse_body = parse_body
        self.parse_query = parse_query
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

    @staticmethod
    def extract_headers(connection: "ASGIConnection[Any, Any, Any]") -> Dict[str, str]:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            A dictionary with the connection's headers.
        """
        return dict(connection.headers)

    @staticmethod
    def extract_cookies(connection: "ASGIConnection[Any, Any, Any]") -> Dict[str, str]:
        """

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Returns:
            A dictionary with the connection's cookies.
        """
        return connection.cookies

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
            output: Dict[str, Any] = {}
            for key, value in form_data.multi_items():
                output[key] = repr(value) if isinstance(value, UploadFile) else value
            return output


class ExtractedResponseData(TypedDict, total=False):
    body: bytes
    status_code: int
    media_type: Union[str, MediaType]
    headers: Dict[str, str]


class ResponseDataExtractor:
    __slots__ = ("extractors",)

    def __init__(
        self,
        extract_body: bool = True,
        extract_status_code: bool = True,
        extract_media_type: bool = True,
        extract_headers: bool = True,
    ):
        """A utility class that extracts data from.

        [Response][starlite.response.Response] instances.

        Args:
            extract_body:
            extract_status_code:
            extract_media_type:
            extract_headers:
        """
        self.extractors: Dict[ResponseExtractorField, Callable[["StarletteResponse"], Any]] = {}
        if extract_body:
            self.extractors["body"] = self.extract_response_body
        if extract_status_code:
            self.extractors["status_code"] = self.extract_status_code
        if extract_media_type:
            self.extractors["media_type"] = self.extract_media_type
        if extract_headers:
            self.extractors["headers"] = self.extract_headers

    def __call__(self, response: "StarletteResponse") -> ExtractedResponseData:
        """Extracts data from the response, returning a dictionary of values.

        Args:
            response: A Starlette or Starlite [Response][starlite.response.Response] instance.

        Returns:
            A string keyed dictionary of extracted values.
        """
        return cast("ExtractedResponseData", {key: extractor(response) for key, extractor in self.extractors.items()})

    @staticmethod
    def extract_response_body(response: "StarletteResponse") -> bytes:
        """

        Args:
            response: A Starlette or Starlite [Response][starlite.response.Response] instance.

        Returns:
            The Response's body as a byte-string.
        """
        return response.body

    @staticmethod
    def extract_status_code(response: "StarletteResponse") -> int:
        """

        Args:
            response: A Starlette or Starlite [Response][starlite.response.Response] instance.

        Returns:
            The Response's status-code.
        """
        return response.status_code

    @staticmethod
    def extract_media_type(response: "StarletteResponse") -> Union[str, MediaType]:
        """

        Args:
            response: A Starlette or Starlite [Response][starlite.response.Response] instance.

        Returns:
            The Response's media_type.
        """
        return response.media_type or MediaType.JSON

    @staticmethod
    def extract_headers(response: "StarletteResponse") -> Dict[str, str]:
        """

        Args:
            response: A Starlette or Starlite [Response][starlite.response.Response] instance.

        Returns:
            The Response's headers.
        """
        return dict(response.headers)
