from __future__ import annotations

from typing import Any

import pytest

from litestar import HttpMethod, MediaType, Request, Response, get, query, route
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.config.response_cache import ResponseCacheConfig
from litestar.exceptions import ImproperlyConfiguredException, NotAuthorizedException
from litestar.params import JSONBody, MsgPackBody, RawBody, URLEncodedBody
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
)
from litestar.testing import create_test_client
from litestar.types import Method


def test_query_request_with_json_body() -> None:
    @query("/search")
    async def handler(data: JSONBody[dict[str, Any]]) -> dict[str, Any]:
        return {"received": data}

    with create_test_client(handler) as client:
        response = client.request("QUERY", "/search", json={"term": "litestar"})
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"received": {"term": "litestar"}}


@pytest.mark.parametrize("http_method", ["QUERY", HttpMethod.QUERY])
def test_route_decorator_with_query_method(http_method: Any) -> None:
    @route("/", http_method=http_method)
    async def handler(data: JSONBody[dict[str, int]]) -> dict[str, int]:
        return data

    with create_test_client(handler) as client:
        response = client.request("QUERY", "/", json={"a": 1})
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"a": 1}


def test_route_decorator_with_get_and_query_methods() -> None:
    @route("/", http_method=["GET", "QUERY"])
    async def handler(request: Request[Any, Any, Any]) -> dict[str, str]:
        return {"method": request.method, "body": (await request.body()).decode()}

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"method": "GET", "body": ""}

        response = client.request("QUERY", "/", content=b"select 1", headers={"content-type": "text/plain"})
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"method": "QUERY", "body": "select 1"}


def test_query_on_get_only_route_is_not_allowed() -> None:
    @get("/")
    async def handler() -> None:
        return None

    with create_test_client(handler) as client:
        response = client.request("QUERY", "/", json={})
        assert response.status_code == HTTP_405_METHOD_NOT_ALLOWED
        assert response.headers["allow"] == "GET, OPTIONS"


def test_get_on_query_only_route_is_not_allowed() -> None:
    @query("/")
    async def handler() -> None:
        return None

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_405_METHOD_NOT_ALLOWED
        assert response.headers["allow"] == "QUERY, OPTIONS"


def test_options_response_lists_query() -> None:
    @route("/", http_method=["GET", "QUERY"])
    async def handler() -> None:
        return None

    with create_test_client(handler) as client:
        response = client.options("/")
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.headers["allow"] == "GET, OPTIONS, QUERY"


def test_csrf_middleware_treats_query_as_safe() -> None:
    @query("/")
    async def handler(data: JSONBody[dict[str, int]]) -> dict[str, int]:
        return data

    with create_test_client(handler, csrf_config=CSRFConfig(secret="secret")) as client:
        response = client.request("QUERY", "/", json={"a": 1})
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"a": 1}
        assert "csrftoken" in response.cookies


@pytest.mark.parametrize(
    "allow_methods, expected_status_code", [(["GET", "QUERY"], HTTP_204_NO_CONTENT), (["GET"], HTTP_400_BAD_REQUEST)]
)
def test_cors_preflight_for_query_with_explicit_methods(allow_methods: list[Any], expected_status_code: int) -> None:
    @query("/")
    async def handler() -> None:
        return None

    cors_config = CORSConfig(allow_origins=["https://example.com"], allow_methods=allow_methods)
    with create_test_client(handler, cors_config=cors_config) as client:
        response = client.options(
            "/", headers={"Origin": "https://example.com", "Access-Control-Request-Method": "QUERY"}
        )
        assert response.status_code == expected_status_code
        if expected_status_code == HTTP_204_NO_CONTENT:
            assert response.headers["access-control-allow-methods"] == "GET, QUERY"


def test_cached_query_responses_are_keyed_by_request_body() -> None:
    calls: list[dict[str, int]] = []

    @query("/", cache=True)
    async def handler(data: JSONBody[dict[str, int]]) -> dict[str, int]:
        calls.append(data)
        return data

    with create_test_client(handler) as client:
        responses = [client.request("QUERY", "/", json=body).json() for body in ({"a": 1}, {"a": 2}, {"a": 1})]

    assert responses == [{"a": 1}, {"a": 2}, {"a": 1}]
    assert calls == [{"a": 1}, {"a": 2}]


def test_cached_query_responses_are_keyed_by_request_body_the_handler_does_not_read() -> None:
    calls = 0

    @query("/", cache=True)
    async def handler() -> int:
        nonlocal calls
        calls += 1
        return calls

    with create_test_client(handler) as client:
        responses = [client.request("QUERY", "/", json=body).json() for body in ({"a": 1}, {"a": 2}, {"a": 1})]

    assert responses == [1, 2, 1]


def test_cached_query_responses_are_keyed_by_media_type() -> None:
    calls: list[str] = []

    @query("/", cache=True)
    async def handler(request: Request[Any, Any, Any], data: JSONBody[dict[str, int]]) -> str:
        calls.append(request.headers["content-type"])
        return request.headers["content-type"]

    with create_test_client(handler) as client:
        responses = [
            client.request("QUERY", "/", content=b'{"a": 1}', headers={"content-type": content_type}).text
            for content_type in ("application/json", "application/vnd.api+json", "application/json")
        ]

    assert responses == ["application/json", "application/vnd.api+json", "application/json"]
    assert calls == ["application/json", "application/vnd.api+json"]


@pytest.mark.parametrize("on_app", [False, True], ids=["handler-key-builder", "app-key-builder"])
def test_cached_query_response_with_custom_key_builder_is_keyed_by_request_body(on_app: bool) -> None:
    calls: list[dict[str, int]] = []

    def key_builder(request: Request[Any, Any, Any]) -> str:
        return request.headers.get("x-tenant", "")

    @query("/", cache=True, cache_key_builder=None if on_app else key_builder)
    async def handler(data: JSONBody[dict[str, int]]) -> dict[str, int]:
        calls.append(data)
        return data

    cache_config = ResponseCacheConfig(key_builder=key_builder) if on_app else ResponseCacheConfig()
    with create_test_client(handler, response_cache_config=cache_config) as client:
        for tenant, value in (("a", 1), ("b", 1), ("a", 1), ("a", 2)):
            client.request("QUERY", "/", json={"a": value}, headers={"x-tenant": tenant})

    assert calls == [{"a": 1}, {"a": 1}, {"a": 2}]


def test_cached_query_handler_whose_guard_fails_before_the_body_is_read() -> None:
    async def guard(connection: Any, handler: Any) -> None:
        raise NotAuthorizedException("denied")

    def handle_denied(request: Request[Any, Any, Any], exc: NotAuthorizedException) -> Response[str]:
        return Response("handled", status_code=HTTP_200_OK, media_type=MediaType.TEXT)

    @query("/", cache=True, guards=[guard], exception_handlers={NotAuthorizedException: handle_denied})
    async def handler() -> str:
        return "ok"

    with create_test_client(handler) as client:
        response = client.request("QUERY", "/", json={"a": 1})

    assert response.status_code == HTTP_200_OK
    assert response.text == "handled"


@pytest.mark.parametrize("http_methods", [["GET", "QUERY"], ["GET", "HEAD"]])
def test_handler_serving_get_cannot_declare_data(http_methods: list[Method]) -> None:
    @route("/", http_method=http_methods)
    async def handler(data: JSONBody[dict[str, int]]) -> None:
        return None

    with (
        pytest.raises(ImproperlyConfiguredException, match="which a handler whose methods include 'GET' does not take"),
        create_test_client(handler),
    ):
        pass


@query("/json")
async def query_json(data: JSONBody[dict[str, int]]) -> dict[str, int]:
    return data


@query("/msgpack")
async def query_msgpack(data: MsgPackBody[dict[str, int]]) -> dict[str, int]:
    return data


@query("/form")
async def query_form(data: URLEncodedBody[dict[str, str]]) -> dict[str, str]:
    return data


@query("/raw")
async def query_raw(body: RawBody) -> int:
    return len(body)


@pytest.mark.parametrize(
    "path, content, content_type, status_code, accept_query",
    [
        ("/json", b'{"a": 1}', None, HTTP_400_BAD_REQUEST, None),
        ("/json", b'{"a": 1}', "text/plain", HTTP_415_UNSUPPORTED_MEDIA_TYPE, "application/json"),
        ("/json", b'{"a": 1}', "application/json; charset=utf-8", HTTP_200_OK, None),
        ("/json", b'{"a": 1}', "application/vnd.api+json", HTTP_200_OK, None),
        ("/json", b"", "application/json", HTTP_400_BAD_REQUEST, None),
        ("/msgpack", b"\x81\xa1a\x01", "application/x-msgpack", HTTP_200_OK, None),
        ("/msgpack", b'{"a": 1}', "application/json", HTTP_415_UNSUPPORTED_MEDIA_TYPE, "application/vnd.msgpack"),
        ("/form", b"a=1", "application/x-www-form-urlencoded", HTTP_200_OK, None),
        (
            "/form",
            b'{"a": 1}',
            "application/json",
            HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "application/x-www-form-urlencoded",
        ),
        ("/raw", b"abc", None, HTTP_400_BAD_REQUEST, None),
        ("/raw", b"abc", "text/csv", HTTP_200_OK, None),
    ],
)
def test_query_request_content_type_must_match_the_declared_body(
    path: str, content: bytes, content_type: str | None, status_code: int, accept_query: str | None
) -> None:
    headers = {"content-type": content_type} if content_type else {}
    with create_test_client([query_json, query_msgpack, query_form, query_raw]) as client:
        response = client.request("QUERY", path, content=content, headers=headers)

    assert response.status_code == status_code
    assert response.headers.get("accept-query") == accept_query


def test_post_request_content_type_is_not_checked() -> None:
    @route("/", http_method=["POST", "QUERY"])
    async def handler(data: JSONBody[dict[str, int]]) -> dict[str, int]:
        return data

    with create_test_client(handler) as client:
        assert client.post("/", content=b'{"a": 1}').status_code == 201
        assert client.request("QUERY", "/", content=b'{"a": 1}').status_code == HTTP_400_BAD_REQUEST
