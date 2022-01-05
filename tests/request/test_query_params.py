from starlite import create_test_request
from starlite.request import parse_query_params


def test_parse_query_params():
    query = {
        "value": "10",
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": "122.53",
        "healthy": True,
        "polluting": False,
    }
    request = create_test_request(query=query)
    result = parse_query_params(connection=request)
    assert result == query
