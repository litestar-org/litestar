from starlette.status import HTTP_200_OK

from examples import hello_world
from starlite.testing import TestClient


def test_hello_world_example() -> None:
    with TestClient(app=hello_world.app) as client:
        r = client.get("/")
    assert r.status_code == HTTP_200_OK
    assert r.json() == {"hello": "world"}
