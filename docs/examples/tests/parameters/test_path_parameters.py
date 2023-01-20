from examples.parameters.path_parameters_1 import app
from examples.parameters.path_parameters_2 import app as app_2
from examples.parameters.path_parameters_3 import app as app_3
from starlite import TestClient


def test_path_parameters_1() -> None:
    with TestClient(app=app) as client:
        res = client.get("/user/1")
        assert res.status_code == 200
        assert res.json() == {"id": 1, "name": "John Doe"}


def test_path_parameters_2() -> None:
    with TestClient(app=app_2) as client:
        res = client.get("/orders/1667924386")
        assert res.status_code == 200
        assert res.json() == [
            {"id": 1, "customer_id": 2},
            {"id": 2, "customer_id": 2},
        ]


def test_path_parameters_3() -> None:
    with TestClient(app=app_3) as client:
        res = client.get("/versions/1")
        assert res.status_code == 200
        assert res.json() == {"id": 1, "specs": {"some": "value"}}
