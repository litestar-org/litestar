import re
from collections import deque
from typing import (
    Any,
    Deque,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from typing_extensions import TypeGuard, get_args

from starlite.types.builtin_types import NoneType
from starlite.utils.predicates import is_class_and_subclass

T = TypeVar("T")
UnionT = TypeVar("UnionT", bound="Union")

tuple_types_regex = re.compile(
    "^"
    + "|".join(
        [*[repr(x) for x in (List, Sequence, Iterable, Iterator, Tuple, Deque)], "tuple", "list", "collections.deque"]
    )
)


def annotation_is_iterable_of_type(
    annotation: Any,
    type_value: Type[T],
) -> "TypeGuard[Iterable[T]]":
    """Determine if a given annotation is an iterable of the given type_value.

    Args:
        annotation: A type annotation.
        type_value: A type value.

    Returns:
        A type-guard boolean.
    """
    if (args := get_args(annotation)) and (
        isinstance(annotation, (List, Sequence, Iterable, Iterator, Tuple, Deque, tuple, list, deque))  # type: ignore
        or tuple_types_regex.match(repr(annotation))
    ):
        return args[0] is type_value or isinstance(args[0], type_value) or is_class_and_subclass(args[0], type_value)
    return False


def make_non_optional_union(annotation: Optional[UnionT]) -> UnionT:
    """Make a :data:`Union <typing.Union>` type that excludes ``NoneType``.

    Args:
        annotation: A type annotation.

    Returns:
        The union with all original members, except ``NoneType``.
    """
    args = tuple(tp for tp in get_args(annotation) if tp is not NoneType)
    return cast("UnionT", Union[args])  # pyright: ignore
