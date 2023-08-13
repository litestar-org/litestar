from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from typing_extensions import get_args, get_origin

from litestar.exceptions import ImproperlyConfiguredException, InvalidAnnotationException
from litestar.typing import FieldDefinition

from .base import Controller

if TYPE_CHECKING:
    from typing import Any


__all__ = ("GenericController",)

T = TypeVar("T")


class GenericController(Controller, Generic[T]):
    """Controller type that supports generic inheritance hierarchies."""

    model_type: type[T]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if not hasattr(cls, "model_type"):
            raise ImproperlyConfiguredException("a model_type attribute must be defined on generic controllers")

        super().__init_subclass__(**kwargs)

    def get_parameter_annotation(self, annotation: Any) -> FieldDefinition:
        """Substitute any ``TypeVar`` in annotation of ``parsed_parameter`` with narrowed type.

        Args:
            annotation: a parsed signature parameter's annotation.
        """
        origin = get_origin(annotation)

        if origin and (parsed_type_args := _parsed_type_args(annotation=annotation, concrete_type=self.model_type)):
            try:
                return FieldDefinition.from_annotation(origin[parsed_type_args])
            except TypeError as e:
                if hasattr(annotation, "copy_with"):
                    return FieldDefinition.from_annotation(annotation.copy_with(parsed_type_args))
                raise InvalidAnnotationException("Unable to rebuild generic type") from e
        return FieldDefinition.from_annotation(annotation)


def _parsed_type_args(annotation: Any, concrete_type: type[Any]) -> tuple[Any, ...] | None:
    """Substitute any ``TypeVar`` for the concrete type.

    Utility for generic controllers.

    Args:
        annotation: annotation to be narrowed.
        concrete_type: concrete type of the narrowed generic controller class.

    Returns:
        A new args tuple if one can be produced, or ``None``.
    """

    if args := get_args(annotation):
        type_var_found = False
        new_args = []
        for arg in args:
            if isinstance(arg, TypeVar):
                new_args.append(concrete_type)
                type_var_found = True
            else:
                new_args.append(arg)

        if not type_var_found:
            return None

        return tuple(new_args)
    return None
