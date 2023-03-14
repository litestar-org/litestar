from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from typing_extensions import Self, get_args, get_origin

from .base import Controller

if TYPE_CHECKING:
    from starlite._signature.parsing import ParsedSignatureParameter

__all__ = ("GenericController",)

T = TypeVar("T")


class GenericController(Controller, Generic[T]):
    """Controller type that supports generic inheritance hierarchies."""

    _data_type: type[T]

    def __class_getitem__(cls, data_type: type[T]) -> type[Self]:
        return type(f"Controller[{data_type.__name__}]", (cls,), {"_data_type": data_type})

    def set_parameter_annotation(self, parsed_parameter: ParsedSignatureParameter) -> None:
        """Substitute any ``TypeVar`` in annotation of ``parsed_parameter`` with narrowed type.

        Args:
            parsed_parameter: a parsed signature parameter - should have a ``TypeVar`` as its type.
        """
        if isinstance(parsed_parameter.annotation, TypeVar):
            parsed_parameter.annotation = self._data_type
            return

        args = get_args(parsed_parameter.annotation)
        origin = get_origin(parsed_parameter.annotation)

        if args and origin:
            new_args = tuple(self._data_type if isinstance(arg, TypeVar) else arg for arg in args)
            try:
                parsed_parameter.annotation = origin[new_args]
            except TypeError as exc:
                if hasattr(parsed_parameter.annotation, "copy_with"):
                    parsed_parameter.annotation = parsed_parameter.annotation.copy_with(new_args)
                else:
                    raise RuntimeError("Unable to rebuild generic type") from exc
