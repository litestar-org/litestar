from litestar import Litestar, Request, Response, get
from litestar.exceptions import HTTPException


def handle_exception(request: Request, exception: Exception) -> Response:
    return Response(
        content={"error": str(exception)},
        status_code=getattr(exception, "status_code", 500),
    )


@get("/boom", sync_to_thread=False)
def boom() -> None:
    raise HTTPException(status_code=418, detail="i am a teapot")


app = Litestar([boom], exception_handlers={HTTPException: handle_exception})

from litestar.testing import TestClient


def test_handler_returns_custom_response() -> None:
    with TestClient(app) as client:
        response = client.get("/boom")
        assert response.status_code == 418
        assert response.json() == {"error": "418: i am a teapot"}
