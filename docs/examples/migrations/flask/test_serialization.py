from litestar import Litestar, MediaType, get


@get("/json", sync_to_thread=False)
def get_json() -> dict[str, str]:
    return {"hello": "world"}


@get("/text", media_type=MediaType.TEXT, sync_to_thread=False)
def get_text() -> str:
    return "hello, world"


@get("/html", media_type=MediaType.HTML, sync_to_thread=False)
def get_html() -> str:
    return "<strong>hello, world</strong>"


app = Litestar([get_json, get_text, get_html])

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_get_json() -> None:
    with TestClient(app) as client:
        response = client.get("/json")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"hello": "world"}


def test_get_text() -> None:
    with TestClient(app) as client:
        response = client.get("/text")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith("text/plain")
        assert response.text == "hello, world"


def test_get_html() -> None:
    with TestClient(app) as client:
        response = client.get("/html")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith("text/html")
        assert response.text == "<strong>hello, world</strong>"
