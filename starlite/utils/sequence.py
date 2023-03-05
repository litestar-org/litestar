from __future__ import annotations

from typing import Callable, Iterable, TypeVar

__all__ = ("find_index", "unique")


T = TypeVar("T")


def find_index(target_list: list[T], predicate: Callable[[T], bool]) -> int:
    """Find element in list given a key and value.

    List elements can be dicts or classes
    """
    for i, element in enumerate(target_list):
        if predicate(element):
            return i
    return -1


def unique(value: Iterable[T]) -> list[T]:
    """Return all unique values in a given sequence or iterator."""
    try:
        return list(set(value))
    except TypeError:
        output: list[T] = []
        for element in value:
            if element not in output:
                output.append(element)
        return output
