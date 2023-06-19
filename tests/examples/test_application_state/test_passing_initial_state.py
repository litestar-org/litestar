from docs.examples.application_state.passing_initial_state import app

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_passing_initial_state_example() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"count": 100}
