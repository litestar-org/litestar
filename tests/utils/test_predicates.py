from collections import defaultdict, deque
from inspect import Signature
from typing import (
    Any,
    DefaultDict,
    Deque,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
)

import pytest

from starlite import CursorPagination, Response, get
from starlite.utils import is_any, is_class_and_subclass, is_optional_union, is_union
from starlite.utils.predicates import (
    is_generic,
    is_mapping,
    is_non_string_iterable,
    is_non_string_sequence,
)


class C:
    pass


@get("/")
def naive_handler() -> Dict[str, int]:
    return {}


@get("/")
def response_handler() -> Response[Any]:
    return Response(content=b"")


class Sub(C):
    ...


@pytest.mark.parametrize(
    "args, expected",
    (
        ((Sub, C), True),
        ((Signature.from_callable(cast("Any", naive_handler.fn.value)).return_annotation, C), False),
        ((Signature.from_callable(cast("Any", response_handler.fn.value)).return_annotation, Response), True),
        ((Dict[str, Any], C), False),
        ((C(), C), False),
    ),
)
def test_is_class_and_subclass(args: tuple, expected: bool) -> None:
    assert is_class_and_subclass(*args) is expected  # pyright: ignore


@pytest.mark.parametrize(
    "value, expected",
    (
        (
            (Tuple[int, ...], True),
            (Tuple[int], True),
            (List[str], True),
            (Set[str], True),
            (FrozenSet[str], True),
            (Deque[str], True),
            (Sequence[str], True),
            (Iterable[str], True),
            (list, True),
            (tuple, True),
            (deque, True),
            (set, True),
            (frozenset, True),
            (str, False),
            (bytes, False),
            (dict, True),
            (Dict[str, Any], True),
            (Union[str, int], False),
            (1, False),
        )
    ),
)
def test_is_non_string_iterable(value: Any, expected: bool) -> None:
    assert is_non_string_iterable(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    (
        (
            (Tuple[int, ...], True),
            (Tuple[int], True),
            (List[str], True),
            (Set[str], True),
            (FrozenSet[str], True),
            (Deque[str], True),
            (Sequence[str], True),
            (Iterable[str], False),
            (list, True),
            (tuple, True),
            (deque, True),
            (set, True),
            (frozenset, True),
            (str, False),
            (bytes, False),
            (dict, False),
            (Dict[str, Any], False),
            (Union[str, int], False),
            (1, False),
        )
    ),
)
def test_is_non_string_sequence(value: Any, expected: bool) -> None:
    assert is_non_string_sequence(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    ((CursorPagination[str, str], True), (dict, False)),
)
def test_is_generic(value: Any, expected: bool) -> None:
    assert is_generic(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    (
        (Dict, True),
        (dict, True),
        (defaultdict, True),
        (DefaultDict, True),
        (Mapping, True),
        (MutableMapping, True),
        (list, False),
        (Iterable, False),
    ),
)
def test_is_mapping(value: Any, expected: bool) -> None:
    assert is_mapping(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    ((Any, True), (Union[Any, str], True), (int, False), (dict, False), (Dict[str, Any], False), (None, False)),
)
def test_is_any(value: Any, expected: bool) -> None:
    assert is_any(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    (
        (Optional[int], True),
        (Optional[Union[int, str]], True),
        (Union[str, None], True),  # noqa: SIM907
        (None, False),
        (int, False),
        (Union[int, str], True),
    ),
)
def test_is_union(value: Any, expected: bool) -> None:
    assert is_union(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    (
        (Optional[int], True),
        (Optional[Union[int, str]], True),
        (Union[str, None], True),  # noqa: SIM907
        (None, False),
        (int, False),
        (Union[int, str], False),
    ),
)
def test_is_optional_union(value: Any, expected: bool) -> None:
    assert is_optional_union(value) is expected
