from starlite.parsers import parse_query_params
from starlite.testing import RequestFactory


def test_parse_query_params() -> None:
    query = {
        "value": "10",
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": "122.53",
        "healthy": True,
        "polluting": False,
    }
    request = RequestFactory().get("/", query_params=query)  # type: ignore[arg-type]
    result = parse_query_params(connection=request)
    assert result == {
        "value": ["10"],
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": ["122.53"],
        "healthy": [True],
        "polluting": [False],
    }
