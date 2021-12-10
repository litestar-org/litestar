from typing import Any, Iterable, List, TypeVar

T = TypeVar("T")


def find_index(target_list: List[T], key: str, value: Any) -> int:
    """Find element in list given a key and value. List elements can be dicts or classes"""
    for i, element in enumerate(target_list):
        if (isinstance(element, dict) and element.get(key) == value) or (
            not isinstance(element, dict) and getattr(element, key) == value
        ):
            return i
    return -1


def unique(value: Iterable[T]) -> List[T]:
    """Return all unique values in a given sequence or iterator"""
    try:
        return list(set(value))
    except TypeError:
        output: List[T] = []
        for element in value:
            if not any(v == element for v in output):
                output.append(element)
        return output
