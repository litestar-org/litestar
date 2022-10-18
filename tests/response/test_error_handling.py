import pytest

from starlite import ImproperlyConfiguredException, MediaType, Response
from starlite.status_codes import HTTP_200_OK


def test_response_error_handling() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Response(content={}, media_type=MediaType.TEXT, status_code=HTTP_200_OK)
