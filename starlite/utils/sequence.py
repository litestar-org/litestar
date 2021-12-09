from typing import Any, Iterable, List, Optional, Sequence, TypeVar, Union, cast

T = TypeVar("T")


def compact(list_to_filter: List[Optional[T]], none_only: bool = False) -> List[T]:
    """
    Removes False values from a given List - if none_only is True,
    only None values are removed, otherwise all False values
    """

    return cast(List[T], list(filter(lambda x: x is not None if none_only else bool(x), list_to_filter)))


def as_iterable(value: Union[T, Sequence[T], Iterable[T]]) -> Iterable[T]:
    """Given a value, return the value if its iterable or a list enveloping it"""
    try:
        iter(value)
        if not isinstance(value, str):
            return value
        return [value]
    except TypeError:
        return [value]


def find(target_list: List[T], key: str, value: Any) -> int:
    """Find element in list given a key and value. List elements can be dicts or classes"""
    for i, el in enumerate(target_list):
        if isinstance(el, dict):
            return i if dict.get(key) == value else -1
        return i if getattr(el, key) == value else -1


def unique(target_list: Union[Sequence[T], Iterable[T]]) -> List[T]:
    return list(set(target_list))
