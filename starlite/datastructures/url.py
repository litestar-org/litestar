from typing import TYPE_CHECKING, Any, NamedTuple, Optional, Union
from urllib.parse import SplitResult, urlsplit, urlunsplit

from starlite.datastructures import Headers

if TYPE_CHECKING:
    from starlite.types import Scope


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


class URL(SplitResult):
    """Namedtuple representing a URL."""

    def __new__(cls, url: Union[str, SplitResult]) -> "URL":
        if isinstance(url, SplitResult):
            result = url
        else:
            result = urlsplit(url)
        return super().__new__(cls, *result)

    def __init__(self, url: Union[str, SplitResult]) -> None:
        # This exists solely for type-checking and documentation purposes
        pass

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
            default_port = {"http": 80, "https": 443, "ws": 80, "wss": 443}[scheme]
            if port != default_port:
                host = f"{host}:{port}"

        return cls.from_components(
            scheme=scheme if server else None,
            query=query_string.decode(),
            netloc=host,
            path=path,
        )

    def with_components(
        self,
        scheme: Optional[str] = None,
        netloc: Optional[str] = None,
        path: Optional[str] = None,
        query: Optional[str] = None,
        fragment: Optional[str] = None,
    ) -> "URL":
        """Create a new URL, replacing the given components.

        Args:
            scheme: URL scheme
            netloc: Network location
            path: Hierarchical path
            query: Query component
            fragment: Fragment identifier

        Returns:
            A new URL with the given components replaced
        """
        return URL.from_components(
            scheme=self.scheme or scheme,
            netloc=self.netloc or netloc,
            path=self.path or path,
            query=self.query or query,
            fragment=self.fragment or fragment,
        )

    def __str__(self) -> str:
        return urlunsplit(self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, URL):
            return super().__eq__(other)
        if isinstance(other, str):
            return str(self) == other
        return NotImplemented
