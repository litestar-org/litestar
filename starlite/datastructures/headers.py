from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Optional

from pydantic import BaseModel, Extra

if TYPE_CHECKING:
    from typing import Any, Dict


class Header(BaseModel, ABC):
    """An abstract type for HTTP headers."""

    HEADER_NAME: ClassVar[str]

    class Config:
        allow_population_by_field_name = True
        extra = Extra.forbid

        @classmethod
        def alias_generator(cls, field_name: str) -> str:  # pylint: disable=missing-function-docstring
            return field_name.replace("_", "-")

    @abstractmethod
    def _get_header_value(self) -> str:
        """Get the header value as string."""

        raise NotImplementedError

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
    s_maxage: Optional[int] = None
    no_cache: Optional[bool] = None
    no_store: Optional[bool] = None
    private: Optional[bool] = None
    public: Optional[bool] = None
    no_transform: Optional[bool] = None
    must_revalidate: Optional[bool] = None
    proxy_revalidate: Optional[bool] = None
    must_understand: Optional[bool] = None
    immutable: Optional[bool] = None
    stale_while_revalidate: Optional[int] = None

    def _get_header_value(self) -> str:
        """Get the header value as string."""

        cc_items = []
        for key, value in self.dict(exclude_unset=True, exclude_none=True, by_alias=True).items():
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
        kwargs: "Dict[str, Any]" = {}
        for cc_item in cc_items:
            key_value = cc_item.split("=")
            if len(key_value) == 1:
                kwargs[key_value[0]] = True
            elif len(key_value) == 2:
                kwargs[key_value[0]] = key_value[1]
            else:
                raise ValueError("Invalid cache-control header value")

        return CacheControlHeader(**kwargs)

    @classmethod
    def prevent_storing(cls) -> "CacheControlHeader":
        """Create a `cache-control` header with the `no-store` directive which
        indicates that any caches of any kind (private or shared) should not
        store this response."""

        return cls(no_store=True)
