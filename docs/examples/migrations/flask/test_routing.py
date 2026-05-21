from litestar import Litestar, get


@get("/", sync_to_thread=False)
def index() -> str:
    return "Index Page"


@get("/hello", sync_to_thread=False)
def hello() -> str:
    return "Hello, World"


app = Litestar([index, hello])

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_index() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Index Page"


def test_hello() -> None:
    with TestClient(app) as client:
        response = client.get("/hello")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello, World"
