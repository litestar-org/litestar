from examples.parameters.path_parameters_3 import app
from starlite import TestClient


def test_path_parameters_3() -> None:
    with TestClient(app=app) as client:
        res = client.get("/versions/1")
        assert res.status_code == 200
        assert res.json() == {"id": 1, "specs": {"some": "value"}}
