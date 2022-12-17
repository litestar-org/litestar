import re
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Tuple,
    Union,
    cast,
)

from multidict import CIMultiDict, CIMultiDictProxy, MultiMapping
from pydantic import BaseModel, Extra, Field, ValidationError, validator
from typing_extensions import Annotated

from starlite.datastructures.multi_dicts import MultiMixin
from starlite.exceptions import ImproperlyConfiguredException
from starlite.parsers import parse_headers

if TYPE_CHECKING:
    from starlite.types.asgi_types import (
        HeaderScope,
        Message,
        RawHeaders,
        RawHeadersList,
    )

ETAG_RE = re.compile(r'([Ww]/)?"(.+)"')


def _encode_headers(headers: Iterable[Tuple[str, str]]) -> "RawHeadersList":
    return [(key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in headers]


class Headers(CIMultiDictProxy[str], MultiMixin[str]):
    """An immutable, case-insensitive for HTTP headers.

    Notes:
        - This class inherits from [multidict](https://multidict.aio-libs.org/en/stable/multidict.html#cimultidictproxy).
    """

    def __init__(self, headers: Optional[Union[Mapping[str, str], "RawHeaders", MultiMapping]] = None) -> None:
        """Initialize `Headers`.

        Args:
            headers: Initial value.
        """
        if not isinstance(headers, MultiMapping):
            headers_: Union[Mapping[str, str], List[Tuple[str, str]]] = {}
            if headers:
                if isinstance(headers, Mapping):
                    headers_ = headers  # pyright: ignore
                else:
                    headers_ = [(key.decode("latin-1"), value.decode("latin-1")) for key, value in headers]

            super().__init__(CIMultiDict(headers_))
        else:
            super().__init__(headers)
        self._header_list: Optional["RawHeadersList"] = None

    @classmethod
    def from_scope(cls, scope: "HeaderScope") -> "Headers":
        """Create headers from a send-message.

        Args:
            scope: The ASGI connection scope.

        Returns:
            Headers

        Raises:
            ValueError: If the message does not have a `headers` key
        """
        if "_headers" not in scope:
            scope["_headers"] = parse_headers(tuple(scope["headers"]))  # type: ignore
        return cls(scope["_headers"])  # type: ignore

    def to_header_list(self) -> "RawHeadersList":
        """Raw header value.

        Returns:
            A list of tuples contain the header and header-value as bytes
        """
        # Since `Headers` are immutable, this can be cached
        header_list = self._header_list
        if not header_list:
            header_list = self._header_list = _encode_headers(
                (key, value) for key in set(self) for value in self.getall(key)
            )
        return header_list  # noqa: R504


class MutableScopeHeaders(MutableMapping):
    """A case-insensitive, multidict-like structure that can be used to mutate headers within a.

    [Scope][starlite.types.Scope]
    """

    def __init__(self, scope: Optional["HeaderScope"] = None) -> None:
        """Initialize `MutableScopeHeaders` from a `HeaderScope`.

        Args:
            scope: The ASGI connection scope.
        """
        self.headers: "RawHeadersList"
        if scope is not None:
            if not isinstance(scope["headers"], list):
                scope["headers"] = list(scope["headers"])

            self.headers = cast("RawHeadersList", scope["headers"])
        else:
            self.headers = []

    @classmethod
    def from_message(cls, message: "Message") -> "MutableScopeHeaders":
        """Construct a header from a message object.

        Args:
            message: [Message][starlite.types.Message].

        Returns:
            MutableScopeHeaders.

        Raises:
            ValueError: If the message does not have a `headers` key.
        """
        if "headers" not in message:
            raise ValueError(f"Invalid message type: {message['type']!r}")

        return cls(cast("HeaderScope", message))

    def add(self, key: str, value: str) -> None:
        """Add a header to the scope.

        Notes:
             - This method keeps duplicates.

        Args:
            key: Header key.
            value: Header value.

        Returns:
            None.
        """
        self.headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    def getall(self, key: str, default: Optional[List[str]] = None) -> List[str]:
        """Get all values of a header.

        Args:
            key: Header key.
            default: Default value to return if `name` is not found.

        Returns:
            A list of strings.

        Raises:
            KeyError: if no header for `name` was found and `default` is not given.
        """
        name = key.lower()
        values = [
            header_value.decode("latin-1")
            for header_name, header_value in self.headers
            if header_name.decode("latin-1").lower() == name
        ]
        if not values:
            if default:
                return default
            raise KeyError
        return values

    def extend_header_value(self, key: str, value: str) -> None:
        """Extend a multivalued header.

        Notes:
            - A multivalues header is a header that can take a comma separated list.
            - If the header previously did not exist, it will be added.

        Args:
            key: Header key.
            value: Header value to add,

        Returns:
            None
        """
        existing = self.get(key)
        if existing is not None:
            value = ",".join([*existing.split(","), value])
        self[key] = value

    def __getitem__(self, key: str) -> str:
        """Get the first header matching `name`"""
        name = key.lower()
        for header in self.headers:
            if header[0].decode("latin-1").lower() == name:
                return header[1].decode("latin-1")
        raise KeyError

    def _find_indices(self, key: str) -> List[int]:
        name = key.lower()
        return [i for i, (name_, _) in enumerate(self.headers) if name_.decode("latin-1").lower() == name]

    def __setitem__(self, key: str, value: str) -> None:
        """Set a header in the scope, overwriting duplicates."""
        name_encoded = key.lower().encode("latin-1")
        value_encoded = value.encode("latin-1")
        indices = self._find_indices(key)
        if not indices:
            self.headers.append((name_encoded, value_encoded))
        else:
            for i in indices[1:]:
                del self.headers[i]
            self.headers[indices[0]] = (name_encoded, value_encoded)

    def __delitem__(self, key: str) -> None:
        """Delete all headers matching `name`"""
        indices = self._find_indices(key)
        for i in indices[::-1]:
            del self.headers[i]

    def __len__(self) -> int:
        """Return the length of the internally stored headers, including duplicates."""
        return len(self.headers)

    def __iter__(self) -> Iterator[str]:
        """Create an iterator of header names including duplicates."""
        return iter(h[0].decode("latin-1") for h in self.headers)


class Header(BaseModel, ABC):
    """An abstract type for HTTP headers."""

    HEADER_NAME: ClassVar[str]

    class Config:
        allow_population_by_field_name = True
        extra = Extra.forbid

        @classmethod
        def alias_generator(cls, field_name: str) -> str:
            """Generate field-aliases by replacing dashes with underscores in header-names."""
            return field_name.replace("_", "-")

    documentation_only: bool = False
    """Defines the header instance as for OpenAPI documentation purpose only."""

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
        """Create a `cache-control` header with the `no-store` directive which indicates that any caches of any kind
        (private or shared) should not store this response.
        """

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
        """Ensure that either value is set or the instance is for documentation_only."""
        if values.get("documentation_only") or value is not None:
            return value
        raise ValueError("value must be set if documentation_only is false")
