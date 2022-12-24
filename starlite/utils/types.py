import re
from collections import deque
from typing import Any, Deque, Iterable, Iterator, List, Sequence, Tuple, Type, TypeVar

from typing_extensions import TypeGuard, get_args

from starlite.utils.predicates import is_class_and_subclass

T = TypeVar("T")

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
