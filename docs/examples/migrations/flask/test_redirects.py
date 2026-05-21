from litestar import Litestar, get
from litestar.response import Redirect


@get("/", sync_to_thread=False)
def index() -> str:
    return "hello"


@get("/hello", sync_to_thread=False)
def hello() -> Redirect:
    return Redirect(path="/")


app = Litestar([index, hello])

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_index_returns_hello() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "hello"


def test_hello_redirects_to_index() -> None:
    with TestClient(app) as client:
        response = client.get("/hello", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/"


def test_hello_follows_to_index() -> None:
    with TestClient(app) as client:
        response = client.get("/hello", follow_redirects=True)
        assert response.status_code == HTTP_200_OK
        assert response.text == "hello"
