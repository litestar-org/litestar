from __future__ import annotations

from typing import Any

import pytest

from litestar import HttpMethod, MediaType, Request, Response, get, head, query, route
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.exceptions import ImproperlyConfiguredException, NotAuthorizedException
from litestar.params import JSONBody
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_405_METHOD_NOT_ALLOWED,
)
from litestar.testing import create_test_client


def test_query_request_with_json_body() -> None:
    @query("/search")
    async def handler(data: JSONBody[dict[str, Any]]) -> dict[str, Any]:
        return {"received": data}

    with create_test_client(handler) as client:
        response = client.request("QUERY", "/search", json={"term": "litestar"})
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"received": {"term": "litestar"}}

        response = client.query("/search", json={"term": "helper"})
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"received": {"term": "helper"}}


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

        response = client.request("QUERY", "/", content=b"select 1")
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


def test_handler_serving_get_and_query_accepts_data() -> None:
    @route("/", http_method=["GET", "QUERY"])
    async def handler(data: JSONBody[dict[str, int] | None] = None) -> dict[str, int]:
        return data or {}

    with create_test_client(handler) as client:
        assert client.get("/").json() == {}
        assert client.request("QUERY", "/", json={"a": 1}).json() == {"a": 1}


def test_cached_query_response_uses_cache_key_builder_of_handler() -> None:
    calls: list[dict[str, int]] = []

    @query("/", cache=True, cache_key_builder=lambda request: request.headers.get("x-tenant", ""))
    async def handler(data: JSONBody[dict[str, int]]) -> dict[str, int]:
        calls.append(data)
        return data

    with create_test_client(handler) as client:
        for tenant in ("a", "b", "a"):
            client.request("QUERY", "/", json={"a": 1}, headers={"x-tenant": tenant})

    assert len(calls) == 2


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


def test_data_on_head_and_get_handlers() -> None:
    @head("/")
    async def head_handler(data: JSONBody[dict[str, int]]) -> None:
        return None

    @route("/get-head", http_method=["GET", "HEAD"])
    async def get_head_handler(data: JSONBody[dict[str, int]]) -> None:
        return None

    with create_test_client(head_handler):
        pass

    with (
        pytest.raises(ImproperlyConfiguredException, match="which a handler whose methods include 'GET' does not take"),
        create_test_client(get_head_handler),
    ):
        pass
