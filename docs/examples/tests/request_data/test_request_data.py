from examples.request_data.request_data_1 import app
from examples.request_data.request_data_2 import app as app_2
from examples.request_data.request_data_3 import app as app_3
from examples.request_data.request_data_4 import app as app_4
from examples.request_data.request_data_5 import app as app_5
from examples.request_data.request_data_6 import app as app_6
from examples.request_data.request_data_7 import app as app_7
from examples.request_data.request_data_8 import app as app_8
from examples.request_data.request_data_9 import app as app_9
from examples.request_data.request_data_10 import app as app_10

from starlite.testing import TestClient


def test_request_data_1() -> None:
    with TestClient(app=app) as client:
        res = client.post("/", json={"hello": "world"})
        assert res.status_code == 201
        assert res.json() == {"hello": "world"}


def test_request_data_2() -> None:
    with TestClient(app=app_2) as client:
        res = client.post("/", json={"id": 1, "name": "John"})
        assert res.status_code == 201
        assert res.json() == {"id": 1, "name": "John"}


def test_request_data_3() -> None:
    with TestClient(app=app_3) as client:
        res = client.post("/", json={"id": 1, "name": "John"})
        assert res.status_code == 201
        assert res.json() == {"id": 1, "name": "John"}


def test_request_data_4() -> None:
    with TestClient(app=app_4) as client:
        res = client.post("/", data={"id": 1, "name": "John"})
        assert res.status_code == 201
        assert res.json() == {"id": 1, "name": "John"}


def test_request_data_5() -> None:
    with TestClient(app=app_5) as client:
        res = client.post(
            "/",
            content=b'--d26a9a4ed2f441fba9ab42d04b42099e\r\nContent-Disposition: form-data; name="id"\r\n\r\n1\r\n--d26a9a4ed2f441fba9ab42d04b42099e\r\nContent-Disposition: form-data; name="name"\r\n\r\nJohn\r\n--d26a9a4ed2f441fba9ab42d04b42099e--\r\n',
            headers={
                "Content-Length": "211",
                "Content-Type": "multipart/form-data; boundary=d26a9a4ed2f441fba9ab42d04b42099e",
            },
        )
        assert res.json() == {"id": 1, "name": "John"}
        assert res.status_code == 201


def test_request_data_6() -> None:
    with TestClient(app=app_6) as client:
        res = client.post("/", files={"upload": ("hello", b"world")})
        assert res.status_code == 201
        assert res.text == "hello, world"


def test_request_data_7() -> None:
    with TestClient(app=app_7) as client:
        res = client.post("/", files={"upload": ("hello", b"world")})
        assert res.status_code == 201
        assert res.text == "hello, world"


def test_request_data_8() -> None:
    with TestClient(app=app_8) as client:
        res = client.post("/", files={"cv": ("cv.odf", b"very impressive"), "diploma": ("diploma.pdf", b"the best")})
        assert res.status_code == 201
        assert res.json() == {"cv": "very impressive", "diploma": "the best"}


def test_request_data_9() -> None:
    with TestClient(app=app_9) as client:
        res = client.post("/", files={"hello": b"there", "i'm": "steve"})
        assert res.status_code == 201
        assert res.json() == {"hello": "there", "i'm": "steve"}


def test_request_data_10() -> None:
    with TestClient(app=app_10) as client:
        res = client.post("/", files={"foo": ("foo.txt", b"hello"), "bar": ("bar.txt", b"world")})
        assert res.status_code == 201
        assert res.json() == {"foo.txt": "hello", "bar.txt": "world"}
