from examples.application_state.using_immutable_state import app
from starlite import TestClient
from starlite.status_codes import HTTP_500_INTERNAL_SERVER_ERROR


def test_using_custom_state_example() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
