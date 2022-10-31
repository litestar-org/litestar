import re
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Iterator, List, Mapping, Optional, Tuple

from multidict import CIMultiDict, CIMultiDictProxy
from pydantic import BaseModel, Extra, Field, ValidationError, validator
from typing_extensions import Annotated

from starlite.exceptions import ImproperlyConfiguredException

ETAG_RE = re.compile(r'([Ww]/)?"(.+)"')


class Headers(CIMultiDictProxy[str, str]):
    """
    An immutable, case-insensitive multidict.
    """

    def __init__(
        self,
        headers: Optional[Mapping[str, str]] = None,
        raw: Optional[List[Tuple[bytes, bytes]]] = None,
        scope: Optional[Mapping[str, Any]] = None,
    ) -> None:
        _list: List[Tuple[str, str]] = []
        if headers is not None:
            assert raw is None, 'Cannot set both "headers" and "raw".'
            assert scope is None, 'Cannot set both "headers" and "scope".'
            _list = [(key.lower(), value) for key, value in headers.items()]
        elif raw is not None:
            assert scope is None, 'Cannot set both "raw" and "scope".'
            _list = [(key.decode("latin-1"), value.decode("latin-1")) for key, value in raw]
        elif scope is not None:
            _list = [(key.decode("latin-1"), value.decode("latin-1")) for key, value in scope["headers"]]
        super().__init__(CIMultiDict(_list))

    @property
    def raw(self) -> List[Tuple[bytes, bytes]]:
        return [(key.encode("latin-1"), value.encode("latin-1")) for key in self for value in self.getlist(key)]

    def getlist(self, key: str) -> List[str]:
        return super().getall(key, [])

    def mutablecopy(self) -> "MutableHeaders":
        return MutableHeaders(raw=self.raw)

    def keys(self) -> List[str]:
        return list(super().keys())

    def values(self) -> List[str]:
        return list(super().values())

    def items(self) -> List[str]:
        return list(super().items())


class MutableHeaders(Mapping[str, str]):
    """
    An immutable, case-insensitive multidict.
    """

    def __init__(
        self,
        headers: Optional[Mapping[str, str]] = None,
        raw: Optional[List[Tuple[bytes, bytes]]] = None,
        scope: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._list: List[Tuple[bytes, bytes]] = []
        if headers is not None:
            assert raw is None, 'Cannot set both "headers" and "raw".'
            assert scope is None, 'Cannot set both "headers" and "scope".'
            self._list = [(key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()]
        elif raw is not None:
            assert scope is None, 'Cannot set both "raw" and "scope".'
            self._list = raw
        elif scope is not None:
            self._list = scope["headers"]

    @property
    def raw(self) -> List[Tuple[bytes, bytes]]:
        return self._list

    def keys(self) -> List[str]:  # type: ignore
        return [key.decode("latin-1") for key, value in self._list]

    def values(self) -> List[str]:  # type: ignore
        return [value.decode("latin-1") for key, value in self._list]

    def items(self) -> List[Tuple[str, str]]:  # type: ignore
        return [(key.decode("latin-1"), value.decode("latin-1")) for key, value in self._list]

    def getlist(self, key: str) -> List[str]:
        get_header_key = key.lower().encode("latin-1")
        return [item_value.decode("latin-1") for item_key, item_value in self._list if item_key == get_header_key]

    def mutablecopy(self) -> "MutableHeaders":
        return MutableHeaders(raw=self._list[:])

    def setdefault(self, key: str, value: str) -> str:
        """
        If the header `key` does not exist, then set it to `value`.
        Returns the header value.
        """
        set_key = key.lower().encode("latin-1")
        set_value = value.encode("latin-1")

        for idx, (item_key, item_value) in enumerate(self._list):
            if item_key == set_key:
                return item_value.decode("latin-1")
        self._list.append((set_key, set_value))
        return value

    def update(self, other: Mapping) -> None:
        for key, val in other.items():
            self[key] = val

    def append(self, key: str, value: str) -> None:
        """
        Append a header, preserving any duplicate entries.
        """
        append_key = key.lower().encode("latin-1")
        append_value = value.encode("latin-1")
        self._list.append((append_key, append_value))

    def add_vary_header(self, vary: str) -> None:
        existing = self.get("vary")
        if existing is not None:
            vary = ", ".join([existing, vary])
        self["vary"] = vary

    def __getitem__(self, key: str) -> str:
        get_header_key = key.lower().encode("latin-1")
        for header_key, header_value in self._list:
            if header_key == get_header_key:
                return header_value.decode("latin-1")
        raise KeyError(key)

    def __contains__(self, key: Any) -> bool:
        get_header_key = key.lower().encode("latin-1")
        for header_key, header_value in self._list:
            if header_key == get_header_key:
                return True
        return False

    def __iter__(self) -> Iterator[Any]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._list)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Headers):
            return False
        return sorted(self.raw) == sorted(other.raw)

    def __setitem__(self, key: str, value: str) -> None:
        """
        Set the header `key` to `value`, removing any duplicate entries.
        Retains insertion order.
        """
        set_key = key.lower().encode("latin-1")
        set_value = value.encode("latin-1")

        found_indexes = []
        for idx, (item_key, item_value) in enumerate(self._list):
            if item_key == set_key:
                found_indexes.append(idx)

        for idx in reversed(found_indexes[1:]):
            del self._list[idx]

        if found_indexes:
            idx = found_indexes[0]
            self._list[idx] = (set_key, set_value)
        else:
            self._list.append((set_key, set_value))

    def __delitem__(self, key: str) -> None:
        """
        Remove the header `key`.
        """
        del_key = key.lower().encode("latin-1")

        pop_indexes = []
        for idx, (item_key, item_value) in enumerate(self._list):
            if item_key == del_key:
                pop_indexes.append(idx)

        for idx in reversed(pop_indexes):
            del self._list[idx]

    def __ior__(self, other: Mapping) -> "MutableHeaders":
        if not isinstance(other, Mapping):
            raise TypeError(f"Expected a mapping but got {other.__class__.__name__}")
        self.update(other)
        return self

    def __or__(self, other: Mapping) -> "MutableHeaders":
        if not isinstance(other, Mapping):
            raise TypeError(f"Expected a mapping but got {other.__class__.__name__}")
        new = self.mutablecopy()
        new.update(other)
        return new


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
