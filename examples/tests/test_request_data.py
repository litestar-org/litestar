from examples.request_data.msgpack_request import app as msgpack_app
from starlite import MediaType, TestClient
from starlite.utils.serialization import encode_msgpack


def test_msgpack_app() -> None:
    test_data = {"name": "Moishe Zuchmir", "age": 30, "programmer": True}

    with TestClient(app=msgpack_app) as client:
        response = client.post(
            "/header", content=encode_msgpack(test_data), headers={"content-type": MediaType.MESSAGEPACK}
        )
        assert response.json() == test_data

        response = client.post("/annotated", content=encode_msgpack(test_data))
        assert response.json() == test_data
