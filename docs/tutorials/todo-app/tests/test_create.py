from examples.create import dataclass as dataclass_app
from examples.create import dict as dict_app

from litestar.testing import TestClient


def test_dict_app() -> None:
    with TestClient(dict_app.app) as client:
        res = client.post("/", json={"title": "foo", "done": True})

        assert res.status_code == 201
        assert res.json() == [{"title": "foo", "done": True}]
        assert dict_app.TODO_LIST == [{"title": "foo", "done": True}]



def test_dataclass_app() -> None:
    with TestClient(dataclass_app.app) as client:
        res = client.post("/", json={"title": "foo", "done": True})

        assert res.status_code == 201
        assert res.json() == [{"title": "foo", "done": True}]
        assert len(dataclass_app.TODO_LIST)
        assert dataclass_app.TODO_LIST[0] == dataclass_app.TodoItem(title="foo", done=True)
