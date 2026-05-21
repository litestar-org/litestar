from litestar import Litestar, Response, get


@get("/static", status_code=404, sync_to_thread=False)
def static_status() -> str:
    return "not found"


@get("/dynamic", sync_to_thread=False)
def dynamic_status() -> Response[str]:
    return Response("not found", status_code=404)


app = Litestar([static_status, dynamic_status])

from litestar.testing import TestClient


def test_static_status() -> None:
    with TestClient(app) as client:
        response = client.get("/static")
        assert response.status_code == 404
        assert response.text == "not found"


def test_dynamic_status() -> None:
    with TestClient(app) as client:
        response = client.get("/dynamic")
        assert response.status_code == 404
        assert response.text == "not found"
