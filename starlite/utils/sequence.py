from typing import Any, Iterable, List, Optional, TypeVar, cast

T = TypeVar("T")


def compact(list_to_filter: List[Optional[T]], none_only: bool = False) -> List[T]:
    """
    Removes False values from a given List - if none_only is True,
    only None values are removed, otherwise all False values
    """

    return cast(List[T], list(filter(lambda x: x is not None if none_only else bool(x), list_to_filter)))


def as_iterable(value: Any) -> Iterable:
    """Given a value, return the value if its iterable or a list enveloping it"""
    try:
        iter(value)
        if not isinstance(value, str):
            return value
        return [value]
    except TypeError:
        return [value]
