import re
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Iterable, List, Mapping, Optional, TYPE_CHECKING, Tuple, Union

from multidict import CIMultiDict, CIMultiDictProxy, MultiMapping
from pydantic import BaseModel, Extra, Field, ValidationError, validator
from typing_extensions import Annotated

from starlite.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from starlite.types.asgi_types import RawHeadersList, Scope

ETAG_RE = re.compile(r'([Ww]/)?"(.+)"')


def _encode_headers(headers: Iterable[Tuple[str, str]]) -> "RawHeadersList":
    return [(key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in headers]


class Headers(CIMultiDictProxy[str]):
    """An immutable, case-insensitive [multidict](https://multidict.aio-
    libs.org/en/stable/multidict.html#cimultidictproxy) for HTTP headers."""

    def __init__(self, headers: Optional[Union[Mapping[str, str], "RawHeadersList", MultiMapping]] = None) -> None:
        if not isinstance(headers, MultiMapping):
            headers_: Union[Mapping[str, str], List[Tuple[str, str]]] = {}
            if isinstance(headers, list):
                headers_ = [(key.decode("latin-1"), value.decode("latin-1")) for key, value in headers]
            elif headers:
                headers_ = headers
            headers_dict = CIMultiDict(headers_)
        else:
            headers_dict = headers
        super().__init__(headers_dict)

    def getall(self, key: str, default: Optional[List[str]] = None) -> List[str]:
        return super().getall(key, default or [])

    @classmethod
    def from_scope(cls, scope: "Scope") -> "Headers":
        """
        Create headers from a send-message.
        Args:
            scope: An ASGI Scope

        Returns:
            Headers

        Raises:
            ValueError: If the message does not have a `headers` key
        """
        return cls(scope["headers"])

    def to_header_list(self) -> "RawHeadersList":
        """Raw header value.

        Returns:
            A list of tuples contain the header and header-value as bytes
        """
        return _encode_headers((key, value) for key in set(self) for value in self.getall(key))


class MutableScopeHeaders:
    def __init__(self, scope: Optional["Scope"] = None) -> None:
        if scope is not None:
            self.headers = scope["headers"]
        else:
            self.headers = []

    def add(self, name: str, value: str) -> None:
        """Add a header to the scope keeping duplicates"""
        self.headers.append((name.lower().encode("latin-1"), value.encode("latin-1")))

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        try:
            return self[name]
        except KeyError:
            return default

    def getall(self, name: str, default: Optional[Tuple[str, ...]] = None) -> Optional[Tuple[str, ...]]:
        name = name.lower()
        values = tuple(
            header_value.decode("latin-1")
            for header_name, header_value in self.headers
            if header_name.decode("latin-1").lower() == name
        )
        return values or default

    def setdefault(self, name: str, value: str) -> str:
        return_value = self.get(name)
        if return_value is None:
            return_value = value
            self[name] = value
        return return_value

    def extend_header_value(self, name: str, value: str) -> None:
        existing = self.get(name)
        if existing is not None:
            value = ", ".join([*existing.split(","), value])
        self[name] = value

    def __getitem__(self, name: str) -> str:
        name = name.lower()
        for header in self.headers:
            if header[0].decode("latin-1").lower() == name:
                return header[1].decode("latin-1")
        raise KeyError

    def __setitem__(self, name: str, value: str) -> None:
        """Set a header in the scope, overwriting duplicates"""
        name = name.lower()
        name_encoded = name.encode("latin-1")
        value_encoded = value.encode("latin-1")
        indices = [i for i, (name_, _) in enumerate(self.headers) if name_.decode("latin-1").lower() == name]
        if not indices:
            self.headers.append((name_encoded, value_encoded))
        else:
            for i in indices[1:]:
                del self.headers[i]
            self.headers[indices[0]] = (name_encoded, value_encoded)

    def __delitem__(self, name: str) -> None:
        name = name.lower()
        for i, header in enumerate(self.headers[::-1]):
            if header[0].decode("latin-1").lower() == name:
                del self.headers[i]

    def __contains__(self, name: str) -> bool:
        name = name.lower()
        return any(h[0].decode("latin-1").lower() == name for h in self.headers)


class Header(BaseModel, ABC):
    """An abstract type for HTTP headers."""

    HEADER_NAME: ClassVar[str]

    class Config:
        allow_population_by_field_name = True
        extra = Extra.forbid

        @classmethod
        def alias_generator(cls, field_name: str) -> str:  # pylint: disable=missing-function-docstring
            return field_name.replace("_", "-")

    documentation_only: bool = False
    """Defines the header instance as for OpenAPI documentation purpose only"""

    @abstractmethod
    def _get_header_value(self) -> str:
        """Get the header value as string."""

        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_header(cls, header_value: str) -> "Header":
        """Construct a header from its string representation."""

    def to_header(self, include_header_name: bool = False) -> str:
        """Get the header as string.

        Args:
            include_header_name: should include the header name in the return value. If set to false
                the return value will only include the header value. if set to true the return value
                will be: `<header name>: <header value>`. Defaults to false.
        """

        if not self.HEADER_NAME:
            raise AttributeError("Missing header name")

        return (f"{self.HEADER_NAME}: " if include_header_name else "") + self._get_header_value()


class CacheControlHeader(Header):
    """A `cache-control` header."""

    HEADER_NAME: ClassVar[str] = "cache-control"

    max_age: Optional[int] = None
    """Accessor for the `max-age` directive."""
    s_maxage: Optional[int] = None
    """Accessor for the `s-maxage` directive."""
    no_cache: Optional[bool] = None
    """Accessor for the `no-cache` directive."""
    no_store: Optional[bool] = None
    """Accessor for the `no-store` directive."""
    private: Optional[bool] = None
    """Accessor for the `private` directive."""
    public: Optional[bool] = None
    """Accessor for the `public` directive."""
    no_transform: Optional[bool] = None
    """Accessor for the `no-transform` directive."""
    must_revalidate: Optional[bool] = None
    """Accessor for the `must-revalidate` directive."""
    proxy_revalidate: Optional[bool] = None
    """Accessor for the `proxy-revalidate` directive."""
    must_understand: Optional[bool] = None
    """Accessor for the `must-understand` directive."""
    immutable: Optional[bool] = None
    """Accessor for the `immutable` directive."""
    stale_while_revalidate: Optional[int] = None
    """Accessor for the `stale-while-revalidate` directive."""

    def _get_header_value(self) -> str:
        """Get the header value as string."""

        cc_items = []
        for key, value in self.dict(
            exclude_unset=True, exclude_none=True, by_alias=True, exclude={"documentation_only"}
        ).items():
            cc_items.append(key if isinstance(value, bool) else f"{key}={value}")

        return ", ".join(cc_items)

    @classmethod
    def from_header(cls, header_value: str) -> "CacheControlHeader":
        """Create a `CacheControlHeader` instance from the header value.

        Args:
            header_value: the header value as string

        Returns:
            An instance of `CacheControlHeader`
        """

        cc_items = [v.strip() for v in header_value.split(",")]
        kwargs: Dict[str, Any] = {}
        for cc_item in cc_items:
            key_value = cc_item.split("=")
            if len(key_value) == 1:
                kwargs[key_value[0]] = True
            elif len(key_value) == 2:
                kwargs[key_value[0]] = key_value[1]
            else:
                raise ImproperlyConfiguredException("Invalid cache-control header value")

        try:
            return CacheControlHeader(**kwargs)
        except ValidationError as exc:
            raise ImproperlyConfiguredException from exc

    @classmethod
    def prevent_storing(cls) -> "CacheControlHeader":
        """Create a `cache-control` header with the `no-store` directive which
        indicates that any caches of any kind (private or shared) should not
        store this response."""

        return cls(no_store=True)


class ETag(Header):
    """An `etag` header."""

    HEADER_NAME: ClassVar[str] = "etag"

    weak: bool = False
    value: Annotated[Optional[str], Field(regex=r"^[ -~]+$")] = None  # only ASCII characters

    def _get_header_value(self) -> str:
        value = f'"{self.value}"'
        if self.weak:
            return f"W/{value}"
        return value

    @classmethod
    def from_header(cls, header_value: str) -> "ETag":
        """Construct an `etag` header from its string representation.

        Note that this will unquote etag-values
        """
        match = ETAG_RE.match(header_value)
        if not match:
            raise ImproperlyConfiguredException
        weak, value = match.group(1, 2)
        try:
            return cls(weak=bool(weak), value=value)
        except ValidationError as exc:
            raise ImproperlyConfiguredException from exc

    @validator("value", always=True)
    def validate_value(cls, value: Any, values: Dict[str, Any]) -> Any:  # pylint: disable=no-self-argument
        """Ensures that either value is set or the instance is for
        documentation_only."""
        if values.get("documentation_only") or value is not None:
            return value
        raise ValueError("value must be set if documentation_only is false")
