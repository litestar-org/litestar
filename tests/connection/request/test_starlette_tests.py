"""The tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_requests.py.
"""

from typing import TYPE_CHECKING, Any, Optional

import pytest
from starlette.datastructures import Address, State
from starlette.status import HTTP_200_OK
from starlette.testclient import TestClient

from starlite import InternalServerException, MediaType
from starlite.connection import Request, empty_send
from starlite.response import Response

if TYPE_CHECKING:
    from starlite.types import Receive, Send


def test_request_url() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        data = {"method": request.method, "url": str(request.url)}
        response = Response(content=data, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/123?a=abc")
    assert response.json() == {"method": "GET", "url": "http://testserver/123?a=abc"}

    response = client.get("https://example.org:123/")
    assert response.json() == {"method": "GET", "url": "https://example.org:123/"}


def test_request_query_params() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        params = dict(request.query_params)
        response = Response(content={"params": params}, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/?a=123&b=456")
    assert response.json() == {"params": {"a": ["123"], "b": ["456"]}}


def test_request_headers() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        headers = dict(request.headers)
        response = Response(content={"headers": headers}, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
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
    [
        ({"client": ["client", 42]}, Address("client", 42)),
        ({"client": None}, None),
        ({}, None),
    ],
)
def test_request_client(scope: Any, expected_client: Optional[Address]) -> None:
    scope.update({"type": "http"})  # required by Request's constructor
    client = Request(scope).client
    assert client == expected_client


def test_request_body() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        body = await request.body()
        response = Response(content={"body": body.decode()}, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore

    response = client.get("/")
    assert response.json() == {"body": ""}

    response = client.post("/", json={"a": "123"})
    assert response.json() == {"body": '{"a": "123"}'}

    response = client.post("/", data="abc")
    assert response.json() == {"body": "abc"}


def test_request_stream() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        body = b""
        async for chunk in request.stream():
            body += chunk
        response = Response(content={"body": body.decode()}, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore

    response = client.get("/")
    assert response.json() == {"body": ""}

    response = client.post("/", json={"a": "123"})
    assert response.json() == {"body": '{"a": "123"}'}

    response = client.post("/", data="abc")
    assert response.json() == {"body": "abc"}


def test_request_form_urlencoded() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        form = await request.form()
        response = Response(content={"form": dict(form)}, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore

    response = client.post("/", data={"abc": "123 @"})
    assert response.json() == {"form": {"abc": "123 @"}}


def test_request_body_then_stream() -> None:
    async def app(scope: "Any", receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        body = await request.body()
        chunks = b""
        async for chunk in request.stream():
            chunks += chunk
        response = Response(
            content={"body": body.decode(), "stream": chunks.decode()},
            status_code=HTTP_200_OK,
            media_type=MediaType.JSON,
        )
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore

    response = client.post("/", data="abc")
    assert response.json() == {"body": "abc", "stream": "abc"}


def test_request_stream_then_body() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        chunks = b""
        async for chunk in request.stream():
            chunks += chunk
        try:
            body = await request.body()
        except InternalServerException:
            body = b"<stream consumed>"
        response = Response(
            content={"body": body.decode(), "stream": chunks.decode()},
            status_code=HTTP_200_OK,
            media_type=MediaType.JSON,
        )
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore

    response = client.post("/", data="abc")
    assert response.json() == {"body": "<stream consumed>", "stream": "abc"}


def test_request_json() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        data = await request.json()
        response = Response(content={"json": data}, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.post("/", json={"a": "123"})
    assert response.json() == {"json": {"a": "123"}}


def test_request_raw_path() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        path = request.scope["path"]
        raw_path = request.scope["raw_path"]
        response = Response(content=f"{path}, {raw_path}", status_code=HTTP_200_OK, media_type=MediaType.TEXT)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/he%2Fllo")
    assert response.text == "/he/llo, b'/he%2Fllo'"


def test_request_without_setting_receive() -> None:
    """If Request is instantiated without the 'receive' channel, then .body()
    is not available."""

    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope)
        try:
            data = await request.json()
        except RuntimeError:
            data = "Receive channel not available"
        response = Response(content={"json": data}, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.post("/", json={"a": "123"})
    assert response.json() == {"json": "Receive channel not available"}


async def test_request_disconnect() -> None:
    """If a client disconnect occurs while reading request body then
    InternalServerException should be raised."""

    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        await request.body()

    async def receiver():
        return {"type": "http.disconnect"}

    scope = {"type": "http", "method": "POST", "path": "/"}
    with pytest.raises(InternalServerException):
        await app(scope, receiver, empty_send)


def test_request_state_object() -> None:
    scope = {"state": {"old": "foo"}}

    s = State(scope["state"])

    s.new = "value"
    assert s.new == "value"

    del s.new

    with pytest.raises(AttributeError):
        s.new


def test_request_state() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        scope["state"] = {}
        request = Request(scope, receive)
        request.state.example = 123
        response = Response(
            content={"state.example": request.state.example}, status_code=HTTP_200_OK, media_type=MediaType.JSON
        )
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/123?a=abc")
    assert response.json() == {"state.example": 123}


def test_request_cookies() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        mycookie = request.cookies.get("mycookie")
        if mycookie:
            response = Response(content=mycookie, media_type="text/plain", status_code=HTTP_200_OK)
        else:
            response = Response(content="Hello, world!", media_type=MediaType.TEXT, status_code=HTTP_200_OK)
            response.set_cookie("mycookie", "Hello, cookies!")

        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.text == "Hello, world!"
    response = client.get("/")
    assert response.text == "Hello, cookies!"


def test_chunked_encoding() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope, receive)
        body = await request.body()
        response = Response(content={"body": body.decode()}, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore

    def post_body():
        yield b"foo"
        yield b"bar"

    response = client.post("/", data=post_body())
    assert response.json() == {"body": "foobar"}


def test_request_send_push_promise() -> None:
    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        # the server is push-enabled
        scope["extensions"]["http.response.push"] = {}

        request = Request(scope, receive, send)
        await request.send_push_promise("/style.css")

        response = Response(content={"json": "OK"}, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.json() == {"json": "OK"}


def test_request_send_push_promise_without_push_extension() -> None:
    """If server does not support the `http.response.push` extension,

    .send_push_promise() does nothing.
    """

    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        request = Request(scope)
        await request.send_push_promise("/style.css")

        response = Response(content={"json": "OK"}, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.json() == {"json": "OK"}


def test_request_send_push_promise_without_setting_send() -> None:
    """If Request is instantiated without the send channel, then.

    .send_push_promise() is not available.
    """

    async def app(scope: Any, receive: "Receive", send: "Send") -> None:
        # the server is push-enabled
        scope["extensions"]["http.response.push"] = {}

        data = "OK"
        request = Request(scope)
        try:
            await request.send_push_promise("/style.css")
        except RuntimeError:
            data = "Send channel not available"
        response = Response(content={"json": data}, status_code=HTTP_200_OK, media_type=MediaType.JSON)
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/")
    assert response.json() == {"json": "Send channel not available"}
