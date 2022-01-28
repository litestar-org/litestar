import pytest
from starlette.status import HTTP_200_OK

from starlite import ImproperlyConfiguredException, MediaType, Response


def test_response_error_handling():
    with pytest.raises(ImproperlyConfiguredException):
        Response(content={}, media_type=MediaType.TEXT, status_code=HTTP_200_OK)
