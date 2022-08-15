from typing import Callable, Iterable, List, TypeVar

T = TypeVar("T")


def find_index(target_list: List[T], predicate: Callable[[T], bool]) -> int:
    """Find element in list given a key and value.

    List elements can be dicts or classes
    """
    for i, element in enumerate(target_list):
        if predicate(element):
            return i
    return -1


def unique(value: Iterable[T]) -> List[T]:
    """Return all unique values in a given sequence or iterator."""
    try:
        return list(set(value))
    except TypeError:
        output: List[T] = []
        for element in value:
            if not any(v == element for v in output):
                output.append(element)
        return output
