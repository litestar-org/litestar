from collections import deque
from typing import Any, Deque, Iterable, Iterator, List, Sequence, Tuple, TypeVar

from typing_extensions import TypeGuard, get_args

T = TypeVar("T")


def annotation_is_iterable_of_type(
    annotation: Any,
    type_value: T,
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
        # for python 3.8 and 3.9 we need to use string comparison rather than isinstance checks.
        or any(
            repr(annotation).startswith(repr(type_variable))
            for type_variable in (List, Sequence, Iterable, Iterator, Tuple, Deque)
        )
    ):
        return args[0] is type_value
    return False
