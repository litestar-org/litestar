from __future__ import annotations

from litestar import get
from litestar.params import FromPath
from litestar.testing import create_test_client


def test_middleware_does_not_leak_state_between_sequential_requests() -> None:
    @get("/cached/{value:str}", cache=True)
    def handler(value: FromPath[str]) -> str:
        return value

    with create_test_client([handler]) as client:
        assert client.get("/cached/first").text == "first"
        assert client.get("/cached/second").text == "second"
        assert client.get("/cached/first").text == "first"
        assert client.get("/cached/second").text == "second"
