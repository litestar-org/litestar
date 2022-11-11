import sys
from dataclasses import is_dataclass
from inspect import isclass
from typing import TYPE_CHECKING, Any, Type, TypeVar, Union

from typing_extensions import ParamSpec, TypeGuard, get_args, get_origin, is_typeddict

from starlite.types.builtin_types import NoneType

if sys.version_info >= (3, 10):
    from types import UnionType

    UNION_TYPES = {UnionType, Union}
else:  # pragma: no cover
    UNION_TYPES = {Union}

if TYPE_CHECKING:

    from starlite.types.builtin_types import (
        DataclassClass,
        DataclassClassOrInstance,
        TypedDictClass,
    )

P = ParamSpec("P")
T = TypeVar("T")


def is_class_and_subclass(value: Any, t_type: Type[T]) -> TypeGuard[Type[T]]:
    """Return `True` if `value` is a `class` and is a subtype of `t_type`.

    See https://github.com/starlite-api/starlite/issues/367

    Args:
        value: The value to check if is class and subclass of `t_type`.
        t_type: Type used for `issubclass()` check of `value`

    Returns:
        bool
    """
    origin = get_origin(value)
    if not origin and not isclass(value):
        return False
    try:
        if origin:
            return origin and issubclass(origin, t_type)
        return issubclass(value, t_type)
    except TypeError:
        return False


def is_optional_union(annotation: Any) -> bool:
    """Given a type annotation determine if the annotation infers an optional union.

    Args:
        annotation: A type.

    Returns:
        True for a union, False otherwise.
    """
    return get_origin(annotation) in UNION_TYPES and NoneType in get_args(annotation)


def is_dataclass_class_typeguard(value: Any) -> "TypeGuard[DataclassClass]":
    """Wrap `is_dataclass()` in a `TypeGuard`, narrowing to type only, not instance.

    Args:
        value: tested to determine if type of `dataclass`.

    Returns:
        `True` if `value` is a `dataclass` type.
    """
    return is_dataclass(value) and isinstance(value, type)


def is_dataclass_class_or_instance_typeguard(value: Any) -> "TypeGuard[DataclassClassOrInstance]":
    """Wrap `is_dataclass()` in a `TypeGuard`.

    Args:
        value: tested to determine if instance or type of `dataclass`.

    Returns:
        `True` if instance or type of `dataclass`.
    """
    return is_dataclass(value)


def is_typeddict_typeguard(value: Any) -> "TypeGuard[TypedDictClass]":
    """Wrap `is_typeddict()` in a `TypeGuard`.

    Args:
        value: tested to determine if instance or type of `dataclass`.

    Returns:
        `True` if instance or type of `dataclass`.
    """
    return is_typeddict(value)
