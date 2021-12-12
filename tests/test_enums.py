import pytest

from starlite import HttpMethod, ImproperlyConfiguredException


@pytest.mark.parametrize(
    "value, expected",
    [
        ["get", True],
        ["post", True],
        ["patch", True],
        ["put", True],
        ["delete", True],
        ["GET", True],
        ["POST", True],
        ["PATCH", True],
        ["PUT", True],
        ["DELETE", True],
        ["ABCD", False],
        [123, False],
    ],
)
def test_http_method_is_http_method(value, expected):
    assert HttpMethod.is_http_method(value) == expected


def test_http_method_from_str():
    for value in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
        assert HttpMethod.from_str(value) in list(HttpMethod)
    with pytest.raises(ImproperlyConfiguredException):
        HttpMethod.from_str("ABCDEFG")
