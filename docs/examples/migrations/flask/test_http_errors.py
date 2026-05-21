from litestar import Litestar, get
from litestar.exceptions import HTTPException


@get("/", sync_to_thread=False)
def index() -> None:
    raise HTTPException(status_code=400, detail="this did not work")


app = Litestar([index])

from litestar.testing import TestClient


def test_index_raises_400() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 400
        assert response.json()["detail"] == "this did not work"
