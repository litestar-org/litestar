from functools import lru_cache
from typing import TYPE_CHECKING, Any, NamedTuple, Optional, Union, cast
from urllib.parse import SplitResult, urlencode, urlsplit, urlunsplit

from starlite.datastructures import MultiDict
from starlite.parsers import parse_query_string
from starlite.types import Empty

if TYPE_CHECKING:
    from starlite.types import EmptyType, Scope

_DEFAULT_SCHEME_PORTS = {"http": 80, "https": 443, "ftp": 21, "ws": 80, "wss": 443}


class Address(NamedTuple):
    """Just a network address."""

    host: str
    """Address host."""
    port: int
    """Address port."""


def make_absolute_url(path: Union[str, "URL"], base: Union[str, "URL"]) -> str:
    """Create an absolute URL.

    Args:
        path: URL path to make absolute
        base: URL to use as a base

    Returns:
        A string representing the new, absolute URL
    """
    url = base if isinstance(base, URL) else URL(base)
    netloc = url.netloc
    path = url.path.rstrip("/") + str(path)
    return str(URL.from_components(scheme=url.scheme, netloc=netloc, path=path))


class URL:
    """Representation and modification utilities of a URL."""

    __slots__ = (
        "_query_params",
        "_parsed_url",
        "fragment",
        "hostname",
        "netloc",
        "password",
        "path",
        "port",
        "query",
        "scheme",
        "username",
    )

    _query_params: Union["EmptyType", "MultiDict"]
    _parsed_url: Optional[str]

    scheme: str
    """URL scheme."""
    netloc: str
    """Network location."""
    path: str
    """Hierarchical path."""
    fragment: str
    """Fragment component."""
    query: str
    """Query string."""
    username: Optional[str]
    """Username if specified."""
    password: Optional[str]
    """Password if specified."""
    port: Optional[int]
    """Port if specified."""
    hostname: Optional[str]
    """Hostname if specified."""

    @lru_cache  # type: ignore[misc]  # noqa: B019
    def __new__(cls, url: Union[str, SplitResult]) -> "URL":
        """Create a new instance.

        Args:
            url: url string or split result to represent.
        """
        instance = super().__new__(cls)
        instance._parsed_url = None

        if isinstance(url, str):
            result = urlsplit(url)
            instance._parsed_url = url
        else:
            result = url

        instance.scheme = result.scheme
        instance.netloc = result.netloc
        instance.path = result.path
        instance.fragment = result.fragment
        instance.query = result.query
        instance.username = result.username
        instance.password = result.password
        instance.port = result.port
        instance.hostname = result.hostname
        instance._query_params = Empty

        return instance

    @property
    def _url(self) -> str:
        if not self._parsed_url:
            self._parsed_url = urlunsplit(
                SplitResult(
                    scheme=self.scheme,
                    netloc=self.netloc,
                    path=self.path,
                    fragment=self.fragment,
                    query=self.query,
                )
            )
        return self._parsed_url

    @classmethod
    @lru_cache
    def from_components(
        cls,
        scheme: str = "",
        netloc: str = "",
        path: str = "",
        fragment: str = "",
        query: str = "",
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
        return cls(  # type: ignore[no-any-return]
            SplitResult(
                scheme=scheme,
                netloc=netloc,
                path=path,
                fragment=fragment,
                query=query,
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
        server = scope.get("server")
        path = scope.get("root_path", "") + scope["path"]
        query_string = scope.get("query_string", b"")

        # # we use iteration here because it's faster, and headers might not yet be cached
        # # in the scope
        host = ""
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"host":
                host = header_value.decode("latin-1")
                break
        if server and not host:
            host, port = server
            default_port = _DEFAULT_SCHEME_PORTS[scheme]
            if port != default_port:
                host = f"{host}:{port}"

        return cls.from_components(
            scheme=scheme if server else "",
            query=query_string.decode(),
            netloc=host,
            path=path,
        )

    def with_replacements(
        self,
        scheme: str = "",
        netloc: str = "",
        path: str = "",
        query: Optional[Union[str, "MultiDict"]] = None,
        fragment: str = "",
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

        return URL.from_components(  # type: ignore[no-any-return]
            scheme=scheme or self.scheme,
            netloc=netloc or self.netloc,
            path=path or self.path,
            query=query or self.query,
            fragment=fragment or self.fragment,
        )

    @property
    def query_params(self) -> "MultiDict":
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
        if self._query_params is Empty:
            self._query_params = MultiDict(parse_query_string(query_string=self.query.encode()))
        return cast("MultiDict", self._query_params)

    def __str__(self) -> str:
        return self._url

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, (str, URL)):
            return str(self) == str(other)
        return NotImplemented  # type: ignore[unreachable]  # pragma: no cover

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._url!r})"
