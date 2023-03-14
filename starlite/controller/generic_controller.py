from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from typing_extensions import Self, get_args, get_origin

from .base import Controller

if TYPE_CHECKING:
    from typing import Any


__all__ = ("GenericController",)

T = TypeVar("T")


class GenericController(Controller, Generic[T]):
    """Controller type that supports generic inheritance hierarchies."""

    _data_type: type[T]

    def __class_getitem__(cls, data_type: type[T]) -> type[Self]:
        return type(f"GenericController[{data_type.__name__}]", (cls,), {"_data_type": data_type})

    def _get_new_args(self, args: tuple[Any, ...], origin: Any | None) -> tuple[Any, ...] | None:
        if not args and origin:
            return None

        type_var_found = False
        new_args = []
        for arg in args:
            if isinstance(arg, TypeVar):
                new_args.append(self._data_type)
                type_var_found = True
                continue
            new_args.append(arg)

        if not type_var_found:
            return None

        return tuple(new_args)

    @staticmethod
    def _rebuild_annotation(original_annotation: Any, origin: Any | None, args_tuple: tuple[Any, ...]) -> Any:
        if origin is None:
            raise RuntimeError("Unexpected origin value")
        try:
            return origin[args_tuple]
        except TypeError as exc:
            if hasattr(original_annotation, "copy_with"):
                return original_annotation.copy_with(args_tuple)
            raise RuntimeError("Unable to rebuild generic type") from exc

    def get_parameter_annotation(self, annotation: Any) -> Any:
        """Substitute any ``TypeVar`` in annotation of ``parsed_parameter`` with narrowed type.

        Args:
            annotation: a parsed signature parameter's annotation.
        """
        if isinstance(annotation, TypeVar):
            return self._data_type

        args = get_args(annotation)
        origin = get_origin(annotation)
        args_tuple = self._get_new_args(args, origin)
        if args_tuple is None:
            return annotation

        return self._rebuild_annotation(annotation, origin, args_tuple)
