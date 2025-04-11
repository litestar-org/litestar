from hashlib import sha256
from io import BytesIO

from docs.examples.request_data.custom_request import app as custom_request_class_app
from docs.examples.request_data.msgpack_request import app as msgpack_app
from docs.examples.request_data.request_data_1 import app
from docs.examples.request_data.request_data_2 import app as app_2
from docs.examples.request_data.test_request_data_3 import app as app_3
from docs.examples.request_data.test_request_data_4 import app as app_4
from docs.examples.request_data.test_request_data_5 import app as app_5
from docs.examples.request_data.test_request_data_6 import app as app_6
from docs.examples.request_data.test_request_data_7 import app as app_7
from docs.examples.request_data.test_request_data_8 import app as app_8
from docs.examples.request_data.test_request_data_9 import app as app_9
from docs.examples.request_data.test_request_data_10 import app as app_10

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
            "file_content": sha256(b"file content").hexdigest(),
        }


def test_request_data_6() -> None:
    with TestClient(app=app_6) as client:
        response = client.post("/", files={"upload": ("hello", b"world")})
        assert response.status_code == 201
        assert response.text == f"hello, {sha256(b'world').hexdigest()}"


def test_request_data_7() -> None:
    with TestClient(app=app_7) as client:
        response = client.post("/", files={"upload": ("hello", b"world")})
        assert response.status_code == 201
        assert response.text == f"hello, {sha256(b'world').hexdigest()}"


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
            "filename": sha256(b"there").hexdigest(),
            "another_filename": sha256(b"steve").hexdigest(),
        }


def test_request_data_10() -> None:
    with TestClient(app=app_10) as client:
        response = client.post("/", files={"foo": ("foo.txt", b"hello"), "bar": ("bar.txt", b"world")})
        assert response.status_code == 201
        assert response.json() == {
            "foo.txt": [
                "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
                "text/plain",
                {"Content-Disposition": 'form-data; name="foo"; filename="foo.txt"', "Content-Type": "text/plain"},
            ],
            "bar.txt": [
                "486ea46224d1bb4fb680f34f7c9ad96a8f24ec88be73ea8e5a6c65260e9cb8a7",
                "text/plain",
                {"Content-Disposition": 'form-data; name="bar"; filename="bar.txt"', "Content-Type": "text/plain"},
            ],
        }


def test_msgpack_app() -> None:
    test_data = {"name": "Moishe Zuchmir", "age": 30, "programmer": True}

    with TestClient(app=msgpack_app) as client:
        response = client.post("/", content=encode_msgpack(test_data))
        assert response.json() == test_data


def test_custom_request_app() -> None:
    with TestClient(app=custom_request_class_app) as client:
        response = client.get("/kitten-name")
        assert response.content == b"Whiskers"
