from starlette.status import HTTP_201_CREATED

from starlite import Body, RequestEncodingType, post
from starlite.testing import create_test_client
from tests.kwargs import Form


def test_request_body_url_encoded() -> None:
    body = Body(media_type=RequestEncodingType.URL_ENCODED)

    test_path = "/test"
    data = Form(name="Moishe Zuchmir", age=30, programmer=True).dict()

    @post(path=test_path)
    def test_method(data: Form = body) -> None:
        assert isinstance(data, Form)

    with create_test_client(test_method) as client:
        response = client.post(test_path, data=data)
        assert response.status_code == HTTP_201_CREATED
