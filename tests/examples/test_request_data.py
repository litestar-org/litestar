import io
from io import BytesIO

from docs.examples.request_data.custom_request import app as custom_request_class_app
from docs.examples.request_data.msgpack_request import app as msgpack_app
from docs.examples.request_data.request_data_1 import app
from docs.examples.request_data.request_data_2 import app as app_2
from docs.examples.request_data.request_data_3 import app as app_3
from docs.examples.request_data.request_data_4 import app as app_4
from docs.examples.request_data.request_data_5 import app as app_5
from docs.examples.request_data.request_data_6 import app as app_6
from docs.examples.request_data.request_data_7 import app as app_7
from docs.examples.request_data.request_data_8 import app as app_8
from docs.examples.request_data.request_data_9 import app as app_9
from docs.examples.request_data.request_data_10 import app as app_10

from litestar.serialization import encode_msgpack
from litestar.testing import TestClient


def test_request_data_1() -> None:
    with TestClient(app=app) as client:
        response = client.post("/", json={"hello": "world"})
        assert response.status_code == 201
        assert response.json() == {"hello": "world"}


def test_request_data_2() -> None:
    with TestClient(app=app_2) as client:
        response = client.post("/", json={"id": 1, "name": "John"})
        assert response.status_code == 201
        assert response.json() == {"id": 1, "name": "John"}


def test_request_data_3() -> None:
    with TestClient(app=app_3) as client:
        response = client.post("/", json={"id": 1, "name": "John"})
        assert response.status_code == 201
        assert response.json() == {"id": 1, "name": "John"}
        schema = client.get("/schema/openapi.json")
        assert "Create a new user." in schema.json()["components"]["schemas"]["User"]["description"]


def test_request_data_4() -> None:
    with TestClient(app=app_4) as client:
        response = client.post("/", data={"id": 1, "name": "John"})
        assert response.status_code == 201
        assert response.json() == {"id": 1, "name": "John"}


def test_request_data_5() -> None:
    with TestClient(app=app_5) as client:
        response = client.post(
            "/",
            files={"form_input_name": ("filename", BytesIO(b"file content"))},
            data={"id": 1, "name": "John"},
        )
        assert response.status_code == 201
        assert response.json() == {
            "id": 1,
            "name": "John",
            "filename": "filename",
            "size": len(b"file content"),
        }


def test_request_data_6() -> None:
    with TestClient(app=app_6) as client:
        response = client.post("/", files={"upload": ("hello", b"world")})
        assert response.status_code == 201
        assert response.text == f"hello,length: {len(b'world')}"


def test_request_data_7() -> None:
    with TestClient(app=app_7) as client:
        response = client.post("/", files={"upload": ("hello", b"world")})
        assert response.status_code == 201
        assert response.text == f"hello,length: {len(b'world')}"


def test_request_data_8() -> None:
    with TestClient(app=app_8) as client:
        response = client.post(
            "/", files={"cv": ("cv.odf", b"very impressive"), "diploma": ("diploma.pdf", b"the best")}
        )
        assert response.status_code == 201
        assert response.json() == {"cv": "very impressive", "diploma": "the best"}


def test_request_data_9() -> None:
    with TestClient(app=app_9) as client:
        response = client.post("/", files={"hello": ("filename", b"there"), "i'm": ("another_filename", "steve")})
        assert response.status_code == 201
        assert response.json() == {
            "filename": len(b"there"),
            "another_filename": len(b"steve"),
        }


def test_request_data_10() -> None:
    with TestClient(app=app_10) as client:
        # if you pass a dict to the `files` parameter without specifying a filename, it will default to `upload
        # so in this app it will be return the last one only...
        #     # file (or bytes)
        response = client.post(
            "/",
            files={
                "will default to upload": io.BytesIO(b"hello world"),
                "will default to upload also": io.BytesIO(b"another"),
            },
        )
        assert response.status_code == 201
        assert response.json().get("upload")[0] != len(b"hello world")
        assert response.json().get("upload")[0] == len(b"another")

        # if you pass the filename explicitly, it will be used as the filename
        #     # (filename, file (or bytes))
        response = client.post("/", files={"file": ("hello.txt", io.BytesIO(b"hello"))})
        assert response.status_code == 201
        assert response.json().get("hello.txt")[0] == len(b"hello")

        # if you add the content type, it will be used as the content type
        #     # (filename, file (or bytes), content_type)
        response = client.post("/", files={"file": ("hello.txt", io.BytesIO(b"hello"), "application/x-bittorrent")})
        assert response.status_code == 201
        assert response.json().get("hello.txt")[0] == len(b"hello")
        assert response.json().get("hello.txt")[1] == "application/x-bittorrent"

        # finally you can specify headers like so
        #     # (filename, file (or bytes), content_type, headers)
        response = client.post(
            "/", files={"file": ("hello.txt", io.BytesIO(b"hello"), "application/x-bittorrent", {"X-Foo": "bar"})}
        )
        assert response.status_code == 201
        assert response.json().get("hello.txt")[0] == len(b"hello")
        assert response.json().get("hello.txt")[1] == "application/x-bittorrent"
        assert ("X-Foo", "bar") in response.json().get("hello.txt")[2].items()


def test_msgpack_app() -> None:
    test_data = {"name": "Moishe Zuchmir", "age": 30, "programmer": True}

    with TestClient(app=msgpack_app) as client:
        response = client.post("/", content=encode_msgpack(test_data))
        assert response.json() == test_data


def test_custom_request_app() -> None:
    with TestClient(app=custom_request_class_app) as client:
        response = client.get("/kitten-name")
        assert response.content == b"Whiskers"
