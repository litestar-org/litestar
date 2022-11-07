from starlite.datastructures.multi_dicts import QueryMultiDict
from starlite.testing import RequestFactory


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
