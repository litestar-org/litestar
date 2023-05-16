from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from litestar.typing import ParsedType

if TYPE_CHECKING:
    from typing import Any, ClassVar

    from typing_extensions import Self

    from litestar.dto.factory._backends.abc import AbstractDTOBackend

T = TypeVar("T")


class DTOData(Generic[T]):
    """DTO validated data and utility methods."""

    __slots__ = ("_backend", "_data_as_builtins")

    parsed_type: ClassVar[ParsedType]

    def __init__(self, backend: AbstractDTOBackend, data_as_builtins: Any) -> None:
        self._backend = backend
        self._data_as_builtins = data_as_builtins

    def __class_getitem__(cls, item: T) -> type[Self]:
        return type(cls.__name__, (cls,), {"parsed_type": ParsedType(item)})

    def create_instance(self, **kwargs: Any) -> T:
        """Create an instance of the DTO validated data.

        Args:
            **kwargs: Additional data to create the instance with. Takes precedence over DTO validated data.
        """
        data = {**self._data_as_builtins, **kwargs}
        return self.parsed_type.annotation(**data)  # type:ignore[no-any-return]

    def update_instance(self, instance: T, **kwargs: Any) -> T:
        """Update an instance with the DTO validated data.

        Args:
            instance: The instance to update.
            **kwargs: Additional data to update the instance with. Takes precedence over DTO validated data.
        """
        data = {**self._data_as_builtins, **kwargs}
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def as_builtins(self) -> Any:
        """Return the DTO validated data as builtins."""
        return self._data_as_builtins
