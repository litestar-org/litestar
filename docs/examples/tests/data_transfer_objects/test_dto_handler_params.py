from __future__ import annotations

from examples.data_transfer_objects.dto_handler_params import app
from starlite.testing import TestClient


def test_app() -> None:
    with TestClient(app=app) as client:
        get_res = client.get("/")
        assert get_res.status_code == 200
        assert get_res.json() == [{"id": 1, "name": "mega-corp", "worth": 123.45}]

        post_res = client.post("/", json={"name": "mega-corp", "worth": 123.45})
        print(post_res.text)
        assert post_res.status_code == 201
        assert post_res.json() == {"name": "mega-corp", "worth": 123.45, "id": 1234567}
