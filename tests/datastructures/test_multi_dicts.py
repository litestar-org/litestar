from typing import Type, Union

import pytest

from starlite.datastructures.multi_dicts import (
    ImmutableMultiDict,
    MultiDict,
    QueryMultiDict,
)
from starlite.testing import RequestFactory


@pytest.mark.parametrize("multi_class", [MultiDict, ImmutableMultiDict])
def test_multi_to_dict(multi_class: Type[Union[MultiDict, ImmutableMultiDict]]) -> None:
    multi = multi_class([("key", "value"), ("key", "value2"), ("key2", "value3")])

    assert multi.dict() == {"key": ["value", "value2"], "key2": ["value3"]}


@pytest.mark.parametrize("multi_class", [MultiDict, ImmutableMultiDict])
def test_multi_multi_items(multi_class: Type[Union[MultiDict, ImmutableMultiDict]]) -> None:
    data = [("key", "value"), ("key", "value2"), ("key2", "value3")]
    multi = multi_class(data)

    assert sorted(multi.multi_items()) == sorted(data)


def test_multi_dict_as_immutable() -> None:
    data = [("key", "value"), ("key", "value2"), ("key2", "value3")]
    multi = MultiDict[str](data)
    assert multi.immutable().dict() == ImmutableMultiDict(data).dict()


def test_immutable_multi_dict_as_mutable() -> None:
    data = [("key", "value"), ("key", "value2"), ("key2", "value3")]
    multi = ImmutableMultiDict[str](data)
    assert multi.mutable_copy().dict() == MultiDict(data).dict()


def test_query_multi_dict_parse_query_params() -> None:
    query = {
        "value": "10",
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": "122.53",
        "healthy": True,
        "polluting": False,
    }
    request = RequestFactory().get(query_params=query)  # type: ignore
    result = QueryMultiDict.from_query_string(query_string=request.scope.get("query_string", b"").decode("utf-8"))

    assert result.getall("value") == ["10"]
    assert result.getall("veggies") == ["tomato", "potato", "aubergine"]
    assert result.getall("calories") == ["122.53"]
    assert result.getall("healthy") == [True]
    assert result.getall("polluting") == [False]

    assert result.dict() == {
        "value": ["10"],
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": ["122.53"],
        "healthy": [True],
        "polluting": [False],
    }
