from starlite import post
from starlite.enums import RequestEncodingType
from starlite.params import Body
from starlite.status_codes import HTTP_201_CREATED
from starlite.testing import create_test_client
from tests.kwargs import Form


def test_request_body_url_encoded() -> None:
    @post(path="/test")
    def test_method(data: Form = Body(media_type=RequestEncodingType.URL_ENCODED)) -> None:
        assert isinstance(data, Form)

    with create_test_client(test_method) as client:
        response = client.post("/test", data=Form(name="Moishe Zuchmir", age=30, programmer=True).dict())
        assert response.status_code == HTTP_201_CREATED
