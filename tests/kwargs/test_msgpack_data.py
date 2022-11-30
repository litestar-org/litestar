from starlite import Body, RequestEncodingType, post
from starlite.status_codes import HTTP_201_CREATED
from starlite.testing import create_test_client
from starlite.utils.serialization import encode_msgpack


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
        response = client.post(
            "/header", content=encode_msgpack(test_data), headers={"content-type": RequestEncodingType.MESSAGEPACK}
        )
        assert response.status_code == HTTP_201_CREATED

        response = client.post("/annotated", content=encode_msgpack(test_data))
        assert response.status_code == HTTP_201_CREATED
