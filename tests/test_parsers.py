from starlite.parsers import parse_query_params
from starlite.testing import create_test_request


def test_parse_query_params() -> None:
    query = {
        "value": "10",
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": "122.53",
        "healthy": True,
        "polluting": False,
    }
    request = create_test_request(query=query)  # type: ignore
    result = parse_query_params(request)
    assert result == {
        "value": ["10"],
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": ["122.53"],
        "healthy": [True],
        "polluting": [False],
    }
