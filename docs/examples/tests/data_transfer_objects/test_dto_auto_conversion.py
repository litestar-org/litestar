from examples.data_transfer_objects.dto_auto_conversion import app
from starlite.testing import TestClient


def test_app() -> None:
    with TestClient(app=app) as client:
        get_res = client.get("/1")
        assert get_res.status_code == 200
        assert get_res.json() == {"id": 1, "name": "My Firm", "worth": 1000000.0}

        get_res = client.get("/")
        assert get_res.status_code == 200
        assert get_res.json() == [
            {"id": 1, "name": "My Firm", "worth": 1000000.0},
            {"id": 2, "name": "My New Firm", "worth": 1000.0},
        ]
