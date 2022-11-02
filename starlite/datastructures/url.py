from typing import TYPE_CHECKING, Any, NamedTuple, Optional, Union
from urllib.parse import SplitResult, urlsplit, urlunsplit

if TYPE_CHECKING:
    from starlite.types import Scope


class Address(NamedTuple):
    host: str
    port: int


def make_absolute_url(url_path: str, base_url: Union[str, "URL"]) -> str:
    if isinstance(base_url, str):
        base_url = URL(base_url)
    netloc = base_url.netloc
    path = base_url.path.rstrip("/") + url_path
    return str(URL.from_components(scheme=base_url.scheme, netloc=netloc, path=path))


class URL(SplitResult):
    def __new__(cls, url: Union[str, SplitResult]) -> "URL":
        if isinstance(url, SplitResult):
            result = url
        else:
            result = urlsplit(url)
        return super().__new__(cls, *result)

    def __init__(self, url: Union[str, SplitResult]) -> None:
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
        result = urlsplit("")
        return cls(
            SplitResult(
                scheme=scheme or result.scheme,
                netloc=netloc or result.netloc,
                path=path or result.path,
                fragment=fragment or result.fragment,
                query=query or result.query,
            )
        )

    @classmethod
    def from_scope(cls, scope: "Scope") -> "URL":
        scheme = scope.get("scheme", "http")
        server = scope.get("server", None)
        path = scope.get("root_path", "") + scope["path"]
        query_string = scope.get("query_string", b"")

        host_header = None
        for key, value in scope["headers"]:
            if key == b"host":
                host_header = value.decode("latin-1")
                break

        if host_header is not None:
            url = f"{scheme}://{host_header}{path}"
        elif server is None:
            url = path
        else:
            host, port = server
            default_port = {"http": 80, "https": 443, "ws": 80, "wss": 443}[scheme]
            if port == default_port:
                url = f"{scheme}://{host}{path}"
            else:
                url = f"{scheme}://{host}:{port}{path}"

        if query_string:
            url += "?" + query_string.decode()
        return cls(url)

    def with_components(
        self,
        scheme: Optional[str] = None,
        netloc: Optional[str] = None,
        path: Optional[str] = None,
        fragment: Optional[str] = None,
        query: Optional[str] = None,
    ) -> "URL":
        return URL.from_components(
            scheme=self.scheme or scheme,
            netloc=self.netloc or netloc,
            path=self.path or path,
            fragment=self.fragment or fragment,
            query=self.query or query,
        )

    def __str__(self) -> str:
        return urlunsplit(self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, URL):
            return super().__eq__(other)
        if isinstance(other, str):
            return str(self) == other
        return NotImplemented
