from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from litestar.utils.signature import ParsedType

if TYPE_CHECKING:
    from typing import Any, ClassVar

    from typing_extensions import Self

    from litestar.dto.factory._backends.abc import AbstractDTOBackend

T = TypeVar("T")


class DTOData(Generic[T]):
    __slots__ = ("_backend", "_data_as_builtins")

    parsed_type: ClassVar[ParsedType]

    def __init__(self, backend: AbstractDTOBackend, data_as_builtins: Any) -> None:
        self._backend = backend
        self._data_as_builtins = data_as_builtins

    def __class_getitem__(cls, item: T) -> type[Self]:
        return type(cls.__name__, (cls,), {"parsed_type": ParsedType(item)})

    def create_instance(self, **kwargs: Any) -> T:
        data = {**self._data_as_builtins, **kwargs}
        return self.parsed_type.annotation(**data)  # type:ignore[no-any-return]

    def as_builtins(self) -> Any:
        return self._data_as_builtins
