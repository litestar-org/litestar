from litestar import get
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client


@get("/", sync_to_thread=False)
def index() -> str:
    return "Index Page"


def test_index() -> None:
    with create_test_client(route_handlers=[index]) as client:
        response = client.get("/")
    assert response.status_code == HTTP_200_OK
    assert response.text == "Index Page"
