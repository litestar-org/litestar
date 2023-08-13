from litestar import post
from litestar.contrib.pydantic import _model_dump
from litestar.params import Body
from litestar.status_codes import HTTP_201_CREATED
from litestar.testing import create_test_client

from . import Form


def test_request_body_json() -> None:
    @post(path="/test")
    def test_method(data: Form = Body()) -> None:
        assert isinstance(data, Form)

    with create_test_client(test_method) as client:
        response = client.post(
            "/test", json=_model_dump(Form(name="Moishe Zuchmir", age=30, programmer=True, value="100"))
        )
        assert response.status_code == HTTP_201_CREATED


def test_empty_dict_allowed() -> None:
    @post(path="/test")
    def test_method(data: dict) -> None:
        assert isinstance(data, dict)

    with create_test_client(test_method) as client:
        response = client.post("/test", json={})
        assert response.status_code == HTTP_201_CREATED
