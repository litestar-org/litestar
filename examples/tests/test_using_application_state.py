import logging
from typing import Any

from examples import using_application_state
from starlite.status_codes import HTTP_200_OK
from starlite.testing import TestClient


def test_using_application_state(caplog: Any) -> None:
    with caplog.at_level(logging.INFO, "examples.using_application_state"):
        with TestClient(app=using_application_state.starlite) as client:
            r = client.get("/")
        assert r.status_code == HTTP_200_OK
    assert {record.getMessage() for record in caplog.records} == {
        "state value in middleware: abc123",
        "state value in dependency: abc123",
        "state value in handler from `State`: abc123",
        "state value in handler from `Request`: abc123",
    }
