import sys
from typing import TYPE_CHECKING, Any, Dict
from unittest.mock import patch

import pytest
from orjson import JSONDecodeError

from starlite import StaticFilesConfig, get
from starlite.connection import Request
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.skipif(sys.version_info < (3, 8), reason="skipping due to python 3.7 async failures")  # type: ignore[misc]
async def test_request_empty_body_to_json(anyio_backend: str) -> None:
    with patch.object(Request, "body", return_value=b""):
        request_empty_payload: Request = Request(scope={"type": "http"})  # type: ignore
        request_json = await request_empty_payload.json()
        assert request_json is None


@pytest.mark.skipif(sys.version_info < (3, 8), reason="skipping due to python 3.7 async failures")  # type: ignore[misc]
async def test_request_invalid_body_to_json(anyio_backend: str) -> None:
    with patch.object(Request, "body", return_value=b"invalid"), pytest.raises(JSONDecodeError):
        request_empty_payload: Request = Request(scope={"type": "http"})  # type: ignore
        await request_empty_payload.json()


@pytest.mark.skipif(sys.version_info < (3, 8), reason="skipping due to python 3.7 async failures")  # type: ignore[misc]
async def test_request_valid_body_to_json(anyio_backend: str) -> None:
    with patch.object(Request, "body", return_value=b'{"test": "valid"}'):
        request_empty_payload: Request = Request(scope={"type": "http"})  # type: ignore
        request_json = await request_empty_payload.json()
        assert request_json == {"test": "valid"}


def test_request_url_for() -> None:
    @get(path="/proxy", name="proxy")
    def proxy() -> None:
        pass

    @get(path="/test")
    def root(request: Request) -> Dict[str, str]:
        return {"url": request.url_for("proxy")}

    @get(path="/test-none")
    def test_none(request: Request) -> Dict[str, str]:
        return {"url": request.url_for("none")}

    with create_test_client(route_handlers=[proxy, root, test_none]) as client:
        response = client.get("/test")
        assert response.json() == {"url": "http://testserver/proxy"}

        response = client.get("/test-none")
        assert response.status_code == 500


def test_request_asset_url(tmp_path: "Path") -> None:
    @get(path="/resolver")
    def resolver(request: Request) -> Dict[str, str]:
        return {"url": request.url_for_static_asset("js", "main.js")}

    @get(path="/resolver-none")
    def resolver_none(request: Request) -> Dict[str, str]:
        return {"url": request.url_for_static_asset("none", "main.js")}

    with create_test_client(
        route_handlers=[resolver, resolver_none],
        static_files_config=StaticFilesConfig(path="/static/js", directories=[tmp_path], name="js"),
    ) as client:
        response = client.get("/resolver")
        assert response.json() == {"url": "http://testserver/static/js/main.js"}

        response = client.get("/resolver-none")
        assert response.status_code == 500


def test_route_handler_property() -> None:
    value: Any = {}

    @get("/")
    def handler(request: Request) -> None:
        value["handler"] = request.route_handler

    with create_test_client(route_handlers=[handler]) as client:
        client.get("/")
        assert value["handler"] is handler


def test_custom_request_class() -> None:
    value: Any = {}

    class MyRequest(Request):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.scope["called"] = True  # type: ignore

    @get("/")
    def handler(request: MyRequest) -> None:
        value["called"] = request.scope.get("called")

    with create_test_client(route_handlers=[handler], request_class=MyRequest) as client:
        client.get("/")
        assert value["called"]
