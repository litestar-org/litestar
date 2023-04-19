from examples import update
from litestar.testing import TestClient


def test_update() -> None:
    with TestClient(update.app) as client:
        res = client.put("/Profit", json={"title": "Profit", "done": True})

        assert res.status_code == 200
        assert update.TODO_LIST[2].done

