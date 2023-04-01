from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import (
    AbstractSet,
    Any,
    DefaultDict,
    Deque,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from typing_extensions import Annotated, NotRequired, Required, TypeGuard, get_args, get_origin

from litestar.types.builtin_types import NoneType

__all__ = ("annotation_is_iterable_of_type", "make_non_optional_union")


T = TypeVar("T")
UnionT = TypeVar("UnionT", bound="Union")

tuple_types_regex = re.compile(
    "^"
    + "|".join(
        [*[repr(x) for x in (List, Sequence, Iterable, Iterator, Tuple, Deque)], "tuple", "list", "collections.deque"]
    )
)

types_mapping = {
    AbstractSet: set,
    DefaultDict: defaultdict,
    Deque: deque,
    Dict: dict,
    FrozenSet: frozenset,
    List: list,
    Mapping: dict,
    MutableMapping: dict,
    MutableSequence: list,
    MutableSet: set,
    Sequence: list,
    Set: set,
    Tuple: tuple,
}


def annotation_is_iterable_of_type(
    annotation: Any,
    type_value: type[T],
) -> TypeGuard[Iterable[T]]:
    """Determine if a given annotation is an iterable of the given type_value.

    Args:
        annotation: A type annotation.
        type_value: A type value.

    Returns:
        A type-guard boolean.
    """
    from litestar.utils.predicates import is_class_and_subclass

    if (args := get_args(annotation)) and (
        isinstance(annotation, (List, Sequence, Iterable, Iterator, Tuple, Deque, tuple, list, deque))  # type: ignore
        or tuple_types_regex.match(repr(annotation))
    ):
        return args[0] is type_value or isinstance(args[0], type_value) or is_class_and_subclass(args[0], type_value)
    return False


def make_non_optional_union(annotation: UnionT | None) -> UnionT:
    """Make a :data:`Union <typing.Union>` type that excludes ``NoneType``.

    Args:
        annotation: A type annotation.

    Returns:
        The union with all original members, except ``NoneType``.
    """
    args = tuple(tp for tp in get_args(annotation) if tp is not NoneType)
    return cast("UnionT", Union[args])  # pyright: ignore


def unwrap_union(annotation: Any) -> tuple[Any, ...]:
    """Unwrap a union type into a tuple of type arguments.

    Args:
        annotation: A union annotation.

    Returns:
        A tuple of annotations
    """
    from litestar.utils.predicates import is_optional_union, is_union

    args: list[Any] = []

    for arg in get_args(annotation):
        arg_value = get_origin_or_inner_type(arg) or arg
        if is_optional_union(arg_value) or is_union(arg_value):
            args.extend(unwrap_union(arg_value))
        else:
            args.append(arg_value)

    return tuple(args)


def get_origin_or_inner_type(annotation: Any) -> Any:
    """Get origin or unwrap it. Returns None for non-generic types.

    Args:
        annotation: A type annotation.

    Returns:
        Any type.
    """

    if origin := get_origin(annotation):
        origin = origin if origin not in (Annotated, Required, NotRequired) else get_args(annotation)[0]
        if origin in types_mapping:  # pragma: no cover
            # py 3.9 and lower compatibility
            return types_mapping[origin]
        return origin
    return None
