from dataclasses import asdict
from typing import Optional

from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.status_codes import HTTP_201_CREATED
from litestar.testing import create_test_client

from . import Form


def test_request_body_url_encoded() -> None:
    @post(path="/test")
    def test_method(data: Form = Body(media_type=RequestEncodingType.URL_ENCODED)) -> None:
        assert isinstance(data, Form)

    with create_test_client(test_method) as client:
        response = client.post("/test", data=asdict(Form(name="Moishe Zuchmir", age=30, programmer=True, value="100")))
        assert response.status_code == HTTP_201_CREATED


def test_optional_request_body_url_encoded() -> None:
    @post(path="/test")
    def test_method(data: Optional[Form] = Body(media_type=RequestEncodingType.URL_ENCODED)) -> None:
        assert data is None

    with create_test_client(test_method) as client:
        response = client.post("/test", data={})
        assert response.status_code == HTTP_201_CREATED
