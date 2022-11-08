from examples.parameters.path_parameters_2 import app
from starlite import TestClient


def test_path_parameters_2() -> None:
    with TestClient(app=app) as client:
        res = client.get("/orders/1667924386")
        assert res.status_code == 200
        assert res.json() == [
            {"id": 1, "customer_id": 2},
            {"id": 2, "customer_id": 2},
        ]
