"""A large part of the tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_requests.py. And are
meant to ensure our compatibility with their API.
"""

from typing import TYPE_CHECKING, Any, Dict, Generator, Optional
from unittest.mock import patch

import pytest
from msgspec import DecodeError

from starlite import InternalServerException, MediaType, StaticFilesConfig, get
from starlite.connection import Request, empty_send
from starlite.datastructures import Address
from starlite.response import Response
from starlite.testing import TestClient, create_test_client

if TYPE_CHECKING:
    from pathlib import Path

    from starlite.types import Receive, Scope, Send


async def test_request_empty_body_to_json(anyio_backend: str) -> None:
    with patch.object(Request, "body", return_value=b""):
        request_empty_payload: Request = Request(scope={"type": "http"})  # type: ignore
        request_json = await request_empty_payload.json()
        assert request_json is None


async def test_request_invalid_body_to_json(anyio_backend: str) -> None:
    with patch.object(Request, "body", return_value=b"invalid"), pytest.raises(DecodeError):
        request_empty_payload: Request = Request(scope={"type": "http"})  # type: ignore
        await request_empty_payload.json()


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
        assert response.json() == {"url": "http://testserver.local/proxy"}

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
        assert response.json() == {"url": "http://testserver.local/static/js/main.js"}

        response = client.get("/resolver-none")
        assert response.status_code == 500


def test_route_handler_property() -> None:
    value: Any = {}

    @get("/")
    def handler(request: Request) -> None:
        value["handler"] = request.route_handler

    with create_test_client(route_handlers=[handler]) as client:
        client.get("/")
        assert str(value["handler"]) == str(handler)


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


def test_request_url() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        data = {"method": request.method, "url": str(request.url)}
        response = Response(content=data)
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/123?a=abc")
    assert response.json() == {"method": "GET", "url": "http://testserver.local/123?a=abc"}

    response = client.get("https://example.org:123/")
    assert response.json() == {"method": "GET", "url": "https://example.org:123/"}


def test_request_query_params() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        params = dict(request.query_params)
        response = Response(content={"params": params})
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/?a=123&b=456")
    assert response.json() == {"params": {"a": "123", "b": "456"}}


def test_request_headers() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        headers = dict(request.headers)
        response = Response(content={"headers": headers})
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/", headers={"host": "example.org"})
    assert response.json() == {
        "headers": {
            "host": "example.org",
            "user-agent": "testclient",
            "accept-encoding": "gzip, deflate, br",
            "accept": "*/*",
            "connection": "keep-alive",
        }
    }


@pytest.mark.parametrize(
    "scope,expected_client",
    (
        ({"type": "http", "client": ["client", 42]}, Address("client", 42)),
        ({"type": "http", "client": None}, None),
        ({"type": "http"}, None),
    ),
)
def test_request_client(scope: "Scope", expected_client: Optional[Address]) -> None:
    client = Request[Any, Any](scope).client
    assert client == expected_client


def test_request_body() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        body = await request.body()
        response = Response(content={"body": body.decode()})
        await response(scope, receive, send)

    client = TestClient(app)

    response = client.get("/")
    assert response.json() == {"body": ""}

    response = client.post("/", json={"a": "123"})
    assert response.json() == {"body": '{"a": "123"}'}

    response = client.post("/", content="abc")
    assert response.json() == {"body": "abc"}


def test_request_stream() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        body = b""
        async for chunk in request.stream():
            body += chunk
        response = Response(content={"body": body.decode()})
        await response(scope, receive, send)

    client = TestClient(app)

    response = client.get("/")
    assert response.json() == {"body": ""}

    response = client.post("/", json={"a": "123"})
    assert response.json() == {"body": '{"a": "123"}'}

    response = client.post("/", content="abc")
    assert response.json() == {"body": "abc"}


def test_request_form_urlencoded() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        form = await request.form()
        response = Response(content={"form": dict(form)})
        await response(scope, receive, send)

    client = TestClient(app)

    response = client.post("/", data={"abc": "123 @"})
    assert response.json() == {"form": {"abc": "123 @"}}


def test_request_body_then_stream() -> None:
    async def app(scope: "Any", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        body = await request.body()
        chunks = b""
        async for chunk in request.stream():
            chunks += chunk
        response = Response(content={"body": body.decode(), "stream": chunks.decode()})
        await response(scope, receive, send)

    client = TestClient(app)

    response = client.post("/", content="abc")
    assert response.json() == {"body": "abc", "stream": "abc"}


def test_request_stream_then_body() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        chunks = b""
        async for chunk in request.stream():
            chunks += chunk
        try:
            body = await request.body()
        except InternalServerException:
            body = b"<stream consumed>"
        response = Response(content={"body": body.decode(), "stream": chunks.decode()})
        await response(scope, receive, send)

    client = TestClient(app)

    response = client.post("/", content="abc")
    assert response.json() == {"body": "<stream consumed>", "stream": "abc"}


def test_request_json() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        data = await request.json()
        response = Response(content={"json": data})
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.post("/", json={"a": "123"})
    assert response.json() == {"json": {"a": "123"}}


def test_request_raw_path() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        path = str(request.scope["path"])
        raw_path = str(request.scope["raw_path"])
        response = Response(content=f"{path}, {raw_path}", media_type=MediaType.TEXT)
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/he%2Fllo")
    assert response.text == "/he/llo, b'/he%2Fllo'"


def test_request_without_setting_receive() -> None:
    """If Request is instantiated without the 'receive' channel, then .body() is not available."""

    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope)
        try:
            data = await request.json()
        except RuntimeError:
            data = "Receive channel not available"
        response = Response(content={"json": data})
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.post("/", json={"a": "123"})
    assert response.json() == {"json": "Receive channel not available"}


async def test_request_disconnect() -> None:
    """If a client disconnect occurs while reading request body then InternalServerException should be raised."""

    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        await request.body()

    async def receiver() -> dict:
        return {"type": "http.disconnect"}

    with pytest.raises(InternalServerException):
        await app({"type": "http", "method": "POST", "path": "/"}, receiver, empty_send)  # type: ignore


def test_request_state() -> None:
    @get("/")
    def handler(request: Request[Any, Any]) -> dict:
        request.state.test = 1
        assert request.state.test == 1
        return request.state.dict()

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == {"test": 1}


def test_request_cookies() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:

        request = Request[Any, Any](scope, receive)
        mycookie = request.cookies.get("mycookie")
        if mycookie:
            response = Response(content=mycookie, media_type="text/plain")
        else:
            response = Response(content="Hello, world!", media_type=MediaType.TEXT)
            response.set_cookie("mycookie", "Hello, cookies!")

        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/")
    assert response.text == "Hello, world!"
    response = client.get("/")
    assert response.text == "Hello, cookies!"


def test_chunked_encoding() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope, receive)
        body = await request.body()
        response = Response(content={"body": body.decode()})
        await response(scope, receive, send)

    client = TestClient(app)

    def post_body() -> Generator[bytes, None, None]:
        yield b"foo"
        yield b"bar"

    response = client.post("/", content=post_body())
    assert response.json() == {"body": "foobar"}


def test_request_send_push_promise() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        # the server is push-enabled
        scope["extensions"]["http.response.push"] = {}  # type: ignore

        request = Request[Any, Any](scope, receive, send)
        await request.send_push_promise("/style.css")

        response = Response(content={"json": "OK"})
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/")
    assert response.json() == {"json": "OK"}


def test_request_send_push_promise_without_push_extension() -> None:
    """If server does not support the `http.response.push` extension,

    .send_push_promise() does nothing.
    """

    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        request = Request[Any, Any](scope)
        await request.send_push_promise("/style.css")

        response = Response(content={"json": "OK"})
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/")
    assert response.json() == {"json": "OK"}


def test_request_send_push_promise_without_setting_send() -> None:
    """If Request is instantiated without the send channel, then.

    .send_push_promise() is not available.
    """

    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        # the server is push-enabled
        scope["extensions"]["http.response.push"] = {}  # type: ignore

        data = "OK"
        request = Request[Any, Any](scope)
        try:
            await request.send_push_promise("/style.css")
        except RuntimeError:
            data = "Send channel not available"
        response = Response(content={"json": data})
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/")
    assert response.json() == {"json": "Send channel not available"}
