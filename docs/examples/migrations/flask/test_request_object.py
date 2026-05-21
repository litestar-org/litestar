from litestar import Litestar, Request, get


@get("/", sync_to_thread=False)
def index(request: Request) -> None:
    print(request.method)


app = Litestar([index])

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_index_reads_request() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
