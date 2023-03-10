from starlite import post
from starlite.enums import RequestEncodingType
from starlite.params import Body
from starlite.serialization import encode_msgpack
from starlite.status_codes import HTTP_201_CREATED
from starlite.testing import create_test_client


def test_request_body_msgpack() -> None:
    test_data = {"name": "Moishe Zuchmir", "age": 30, "programmer": True}

    @post(path="/header")
    def test_header(data: dict) -> None:
        assert isinstance(data, dict)
        assert data == test_data

    @post(path="/annotated")
    def test_annotated(data: dict = Body(media_type=RequestEncodingType.MESSAGEPACK)) -> None:
        assert isinstance(data, dict)
        assert data == test_data

    with create_test_client([test_header, test_annotated]) as client:
        response = client.post("/annotated", content=encode_msgpack(test_data))
        assert response.status_code == HTTP_201_CREATED
