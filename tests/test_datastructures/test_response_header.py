import pytest

from litestar.datastructures import ResponseHeader
from litestar.exceptions import ImproperlyConfiguredException


def test_response_headers_validation() -> None:
    ResponseHeader(name="test", documentation_only=True)
    with pytest.raises(ImproperlyConfiguredException):
        ResponseHeader(name="test")
