import pytest
from http.client import HTTPException as StdlibHTTPException

from litestar import get, Litestar
from litestar.response import Response
from litestar.exceptions import ImproperlyConfiguredException


@get("/")
def index() -> None:
    return None


def test_detect_stdlib_http_exception() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[index], exception_handlers={StdlibHTTPException: lambda req, exc: Response(status_code=500)})

