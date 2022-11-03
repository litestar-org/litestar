from typing import TYPE_CHECKING, Any, NamedTuple, Optional, Union
from urllib.parse import SplitResult, parse_qs, urlencode, urlsplit, urlunsplit

from multidict import MultiDict

from starlite.datastructures import Headers

if TYPE_CHECKING:
    from starlite.types import Scope


QueryParamValue = Union[str, bool, int]
QueryParams = MultiDict[QueryParamValue]


class Address(NamedTuple):
    """Just a network address."""

    host: str
    port: int


def make_absolute_url(path: Union[str, "URL"], base: Union[str, "URL"]) -> str:
    """Create an absolute URL.

    Args:
        path: URL path to make absolute
        base: URL to use as a base

    Returns:
        A string representing the new, absolute URL
    """
    if isinstance(base, str):
        base = URL(base)
    netloc = base.netloc
    path = base.path.rstrip("/") + str(path)
    return str(URL.from_components(scheme=base.scheme, netloc=netloc, path=path))


_boolean_values = {"true": True, "1": True, "false": False, "0": False}


def _parse_param_value(value: str) -> QueryParamValue:
    if value.isdigit():
        return int(value)
    return _boolean_values.get(value.lower(), value)


def parse_query_params(query: str) -> QueryParams:
    """Parse query params from a string into a.

    [MultiDict][multidict.MultiDict]. Coerces parameter values into `str`,
    `int` and `bool` where appropriate.

    Args:
        query: The query string

    Returns:
        A mutable [MultiDict][multidict.MultiDict]
    """
    params = parse_qs(query, keep_blank_values=True)
    unwrapped_params = [(param, _parse_param_value(value)) for param, values in params.items() for value in values]
    return MultiDict(unwrapped_params)


class URL:
    __slots__ = (
        "scheme",
        "netloc",
        "path",
        "fragment",
        "query",
        "username",
        "password",
        "port",
        "hostname",
        "_query_params",
        "_url",
    )

    scheme: str
    """URL scheme"""
    netloc: str
    """Network location"""
    path: str
    """Hierarchical path"""
    fragment: str
    """Fragment component"""
    query: str
    """Query string"""
    username: Optional[str]
    """Username if specified"""
    password: Optional[str]
    """Password if specified"""
    port: Optional[int]
    """Port if specified"""
    hostname: Optional[str]
    """Hostname if specified"""

    def __init__(self, url: Union[str, SplitResult]) -> None:
        """Representation and modification utilities of a URL.

        Args:
            url: URL, either as a string or a [SplitResult][urllib.parse.SplitResult] as returned by [urlsplit][urllib.parse.urlsplit]
        """
        if isinstance(url, str):
            result = urlsplit(url)
            self._url = url
        else:
            result = url
            self._url = urlunsplit(url)

        self.scheme = result.scheme
        self.netloc = result.netloc
        self.path = result.path
        self.fragment = result.fragment
        self.query = result.query
        self.username = result.username
        self.password = result.password
        self.port = result.port
        self.hostname = result.hostname
        self._query_params: Optional[QueryParams] = None

    @classmethod
    def from_components(
        cls,
        scheme: Optional[str] = None,
        netloc: Optional[str] = None,
        path: Optional[str] = None,
        fragment: Optional[str] = None,
        query: Optional[str] = None,
    ) -> "URL":
        """Create a new URL from components.

        Args:
            scheme: URL scheme
            netloc: Network location
            path: Hierarchical path
            query: Query component
            fragment: Fragment identifier

        Returns:
            A new URL with the given components
        """
        return cls(
            SplitResult(
                scheme=scheme or "",
                netloc=netloc or "",
                path=path or "",
                fragment=fragment or "",
                query=query or "",
            )
        )

    @classmethod
    def from_scope(cls, scope: "Scope") -> "URL":
        """Construct a URL from a [Scope][starlite.types.Scope]

        Args:
            scope: A scope

        Returns:
            A URL
        """
        scheme = scope.get("scheme", "http")
        server = scope.get("server", None)
        path = scope.get("root_path", "") + scope["path"]
        query_string = scope.get("query_string", b"")

        host = Headers.from_scope(scope).get("host")
        if server and not host:
            host, port = server
            default_port = {"http": 80, "https": 443, "ftp": 21, "ws": 80, "wss": 443}[scheme]
            if port != default_port:
                host = f"{host}:{port}"

        return cls.from_components(
            scheme=scheme if server else None,
            query=query_string.decode(),
            netloc=host,
            path=path,
        )

    def with_replacements(
        self,
        scheme: Optional[str] = None,
        netloc: Optional[str] = None,
        path: Optional[str] = None,
        query: Optional[Union[str, QueryParams]] = None,
        fragment: Optional[str] = None,
    ) -> "URL":
        """Create a new URL, replacing the given components.

        Args:
            scheme: URL scheme
            netloc: Network location
            path: Hierarchical path
            query: Raw query string
            fragment: Fragment identifier

        Returns:
            A new URL with the given components replaced
        """
        if isinstance(query, MultiDict):
            query = urlencode(query=query)
        return URL.from_components(
            scheme=self.scheme or scheme,
            netloc=self.netloc or netloc,
            path=self.path or path,
            query=self.query or query,
            fragment=self.fragment or fragment,
        )

    @property
    def query_params(self) -> QueryParams:
        """Query parameters of a URL as a [MultiDict][multidict.MultiDict]

        Returns:
            A [MultiDict][multidict.MultiDict] with query parameters

        Notes:
            - While the returned `MultiDict` is mutable, [URL][starlite.datastructures.URL]
                itself is *immutable*, therefore mutating the query parameters will not
                directly mutate the `URL`. If you want to modify query parameters, make
                modifications in the multidict and pass them back to
                [with_replacements][starlite.datastructures.URL.with_replacements]
        """
        if self._query_params is None:
            self._query_params = parse_query_params(self.query)
        return self._query_params

    def __str__(self) -> str:
        return self._url

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, (str, URL)):
            return str(self) == str(other)
        return NotImplemented
