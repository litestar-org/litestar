import pytest

from starlite import ImproperlyConfiguredException, MediaType, Response


def test_response_error_handling() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Response(content={}, media_type=MediaType.TEXT)
