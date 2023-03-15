from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from typing_extensions import Self, get_args, get_origin

from starlite.exceptions import StarliteException

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

    def get_parameter_annotation(self, annotation: Any) -> Any:
        """Substitute any ``TypeVar`` in annotation of ``parsed_parameter`` with narrowed type.

        Args:
            annotation: a parsed signature parameter's annotation.
        """
        if isinstance(annotation, TypeVar):
            return self._data_type

        args = get_args(annotation)
        origin = get_origin(annotation)
        new_args = _get_new_args(args, origin, self._data_type)
        if new_args is None:
            return annotation

        return _rebuild_annotation(annotation, origin, new_args)


def _get_new_args(args: tuple[Any, ...], origin: Any | None, concrete_type: type[Any]) -> tuple[Any, ...] | None:
    """Substitute any ``TypeVar`` for the concrete type.

    Utility for generic controllers.

    Args:
        args: response from ``get_args()``
        origin: response from ``get_origin()``
        concrete_type: concrete type of the narrowed generic controller class.

    Returns:
        A new args tuple if one can be produced, or ``None``.
    """
    if not args and origin:
        return None

    type_var_found = False
    new_args = []
    for arg in args:
        if isinstance(arg, TypeVar):
            new_args.append(concrete_type)
            type_var_found = True
            continue
        new_args.append(arg)

    if not type_var_found:
        return None

    return tuple(new_args)


def _rebuild_annotation(original_annotation: Any, origin: Any | None, args_tuple: tuple[Any, ...]) -> Any:
    """Rebuild a generic type with new args.

    Args:
        original_annotation: the unmodified parameter annotation.
        origin: response of ``get_origin()`` for ``original_annotation``.
        args_tuple: response of ``get_args()`` for ``original_annotation``.

    Returns:
        Generic type of ``original_annotation`` narrowed with ``args_tuple``.
    """
    if origin is None:
        raise StarliteException("Unexpected origin value")
    try:
        return origin[args_tuple]
    except TypeError as exc:
        # Note:
        #   On 3.8, ``origin`` may be a builtin collection type which cannot be indexed.
        #
        #   `copy_with()` is a method on the generic types in the `typing` module that creates a new generic type
        #     given the supplied args.
        if hasattr(original_annotation, "copy_with"):
            return original_annotation.copy_with(args_tuple)
        raise StarliteException("Unable to rebuild generic type") from exc
