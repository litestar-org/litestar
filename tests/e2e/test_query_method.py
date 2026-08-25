from typing import Any, get_args

from litestar import HttpMethod, query
from litestar.handlers import query as handlers_query
from litestar.handlers.http_handlers import query as http_handlers_query
from litestar.status_codes import HTTP_413_REQUEST_ENTITY_TOO_LARGE
from litestar.testing import create_test_client
from litestar.types.asgi_types import HttpMethodName


def test_query_public_api_exports() -> None:
    assert HttpMethod.QUERY == "QUERY"
    assert "QUERY" in get_args(HttpMethodName)
    assert handlers_query is query
    assert http_handlers_query is query


def test_query_decorator_configures_route_handler() -> None:
    @query("/search", sync_to_thread=False)
    def handler() -> dict[str, str]:
        return {"method": "QUERY"}

    assert handler.http_methods == {"QUERY"}
    assert handler.include_in_schema is False


def test_query_route_handler() -> None:
    @query("/search", sync_to_thread=False)
    def handler() -> dict[str, str]:
        return {"method": "QUERY"}

    with create_test_client(route_handlers=[handler], openapi_config=None) as client:
        response = client.request("QUERY", "/search")

    assert response.status_code == 200
    assert response.json() == {"method": "QUERY"}


def test_query_route_handler_receives_json_body() -> None:
    @query("/search", sync_to_thread=False)
    def handler(data: dict[str, Any]) -> dict[str, Any]:
        return data

    with create_test_client(route_handlers=[handler], openapi_config=None) as client:
        response = client.request("QUERY", "/search", json={"term": "litestar"})

    assert response.status_code == 200
    assert response.json() == {"term": "litestar"}


def test_query_route_handler_respects_request_max_body_size() -> None:
    @query("/search", request_max_body_size=1, sync_to_thread=False)
    def handler(data: dict[str, Any]) -> dict[str, Any]:
        return data

    with create_test_client(route_handlers=[handler], openapi_config=None) as client:
        response = client.request("QUERY", "/search", json={"term": "litestar"})

    assert response.status_code == HTTP_413_REQUEST_ENTITY_TOO_LARGE


def test_query_route_handler_is_excluded_from_openapi_schema_by_default() -> None:
    @query("/search", sync_to_thread=False)
    def handler() -> dict[str, str]:
        return {"method": "QUERY"}

    with create_test_client(route_handlers=[handler]) as client:
        assert "/search" not in client.app.openapi_schema.to_schema()["paths"]
