from functools import reduce
from operator import iconcat
from typing import Iterable, List, Optional, TypeVar, cast

T = TypeVar("T")


def flatten(value: list) -> list:
    """Flatten a given list"""
    return reduce(iconcat, value, [])


def compact(list_to_filter: Iterable[Optional[T]]) -> List[T]:
    """Filter all None values from a given list"""
    return cast(List[T], list(filter(lambda x: x is not None, list_to_filter)))
