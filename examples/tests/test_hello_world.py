from starlette.status import HTTP_200_OK

import examples
from starlite.testing import TestClient


async def test_hello_world_example() -> None:
    with TestClient(app=examples.hello_world.app) as client:
        r = client.get("/")
    assert r.status_code == HTTP_200_OK
    assert r.json() == {"hello": "world"}
