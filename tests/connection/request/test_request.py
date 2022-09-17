import sys
from typing import Any
from unittest.mock import patch

import pytest
from orjson import JSONDecodeError

from starlite import get
from starlite.connection import Request
from starlite.testing import create_test_client


@pytest.mark.skipif(sys.version_info < (3, 8), reason="skipping due to python 3.7 async failures")  # type: ignore[misc]
@pytest.mark.asyncio()  # type: ignore[misc]
async def test_request_empty_body_to_json() -> None:
    with patch.object(Request, "body", return_value=b""):
        request_empty_payload: Request = Request(scope={"type": "http"})  # type: ignore
        request_json = await request_empty_payload.json()
        assert request_json is None


@pytest.mark.skipif(sys.version_info < (3, 8), reason="skipping due to python 3.7 async failures")  # type: ignore[misc]
@pytest.mark.asyncio()  # type: ignore[misc]
async def test_request_invalid_body_to_json() -> None:
    with patch.object(Request, "body", return_value=b"invalid"), pytest.raises(JSONDecodeError):
        request_empty_payload: Request = Request(scope={"type": "http"})  # type: ignore
        await request_empty_payload.json()


@pytest.mark.skipif(sys.version_info < (3, 8), reason="skipping due to python 3.7 async failures")  # type: ignore[misc]
@pytest.mark.asyncio()  # type: ignore[misc]
async def test_request_valid_body_to_json() -> None:
    with patch.object(Request, "body", return_value=b'{"test": "valid"}'):
        request_empty_payload: Request = Request(scope={"type": "http"})  # type: ignore
        request_json = await request_empty_payload.json()
        assert request_json == {"test": "valid"}


def test_request_resolve_url() -> None:
    @get(path="/proxy", name="proxy")
    def proxy() -> None:
        pass

    @get(path="/test")
    def root(request: Request) -> dict:
        return {"url": request.url_for("proxy")}

    with create_test_client(route_handlers=[proxy, root]) as client:
        response = client.get("/test")
        assert response.json() == {"url": "http://testserver/proxy"}


def test_route_handler_property() -> None:
    value: Any = {}

    @get("/")
    def handler(request: Request) -> None:
        value["handler"] = request.route_handler

    with create_test_client(route_handlers=[handler]) as client:
        client.get("/")
        assert value["handler"] is handler
