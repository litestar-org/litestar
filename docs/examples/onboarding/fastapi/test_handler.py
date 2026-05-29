from typing import Dict

from litestar import get
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client


@get("/", sync_to_thread=False)
def hello() -> Dict[str, str]:
    return {"hello": "world"}


def test_hello() -> None:
    with create_test_client(route_handlers=[hello]) as client:
        response = client.get("/")
    assert response.status_code == HTTP_200_OK
    assert response.json() == {"hello": "world"}
