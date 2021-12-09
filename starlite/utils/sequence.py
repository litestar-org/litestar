from contextlib import suppress
from typing import Any, Iterable, List, Optional, Sequence, TypeVar, Union, cast

T = TypeVar("T")


def compact(list_to_filter: List[Optional[T]], none_only: bool = False) -> List[T]:
    """
    Removes False values from a given List - if none_only is True,
    only None values are removed, otherwise all False values
    """

    return cast(List[T], list(filter(lambda x: x is not None if none_only else bool(x), list_to_filter)))


def as_list(value: Union[T, Sequence[T], Iterable[T]]) -> List[T]:
    """Given a value, return the value enveloped as a list, unless it's already a list"""
    if not isinstance(value, str):
        with suppress(TypeError):
            return list(iter(cast(Iterable[T], value)))
    return cast(List[T], [value])


def find(target_list: List[T], key: str, value: Any) -> int:
    """Find element in list given a key and value. List elements can be dicts or classes"""
    for i, element in enumerate(target_list):
        if (isinstance(element, dict) and element.get(key) == value) or (
            not isinstance(element, dict) and getattr(element, key) == value
        ):
            return i
    return -1


def unique(value: Iterable[T]) -> List[T]:
    """Return all unique values in a given sequence or iterator"""
    return list(set(value))
