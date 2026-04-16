"""Tests for OpenAPI schema generation from typed reserved kwargs (query, headers, cookies).

See: https://github.com/litestar-org/litestar/issues/2015
"""

from __future__ import annotations

from typing import TypedDict

from litestar import Litestar, get
from litestar.enums import ParamType
from litestar.openapi import OpenAPIConfig
from litestar.openapi.spec.enums import OpenAPIType
from litestar.openapi.spec.parameter import Parameter
from litestar.testing import create_test_client


class QueryParams(TypedDict, total=False):
    page: int
    search: str


class RequiredQueryParams(TypedDict):
    page: int
    search: str


class HeaderParams(TypedDict, total=False):
    x_api_key: str
    x_request_id: str


class CookieParams(TypedDict, total=False):
    session_id: str
    tracking_id: str


class TestTypedDictQueryParameters:
    """Test that a TypedDict annotation on the ``query`` reserved kwarg
    generates individual query parameters in the OpenAPI schema."""

    def test_typeddict_query_generates_parameters(self) -> None:
        @get("/items")
        async def handler(query: QueryParams) -> dict:
            return {}

        app = Litestar(route_handlers=[handler])
        parameters = app.openapi_schema.paths["/items"].get.parameters  # type: ignore[index, union-attr]
        assert parameters is not None

        params = [p for p in parameters if isinstance(p, Parameter)]
        param_names = {p.name for p in params}
        assert "page" in param_names
        assert "search" in param_names

    def test_typeddict_query_param_types_are_correct(self) -> None:
        @get("/items")
        async def handler(query: QueryParams) -> dict:
            return {}

        app = Litestar(route_handlers=[handler])
        parameters = app.openapi_schema.paths["/items"].get.parameters  # type: ignore[index, union-attr]
        assert parameters is not None

        params = {p.name: p for p in parameters if isinstance(p, Parameter)}

        assert params["page"].param_in == ParamType.QUERY
        assert params["page"].schema and params["page"].schema.type == OpenAPIType.INTEGER  # type: ignore[union-attr]
        assert params["search"].param_in == ParamType.QUERY
        assert params["search"].schema and params["search"].schema.type == OpenAPIType.STRING  # type: ignore[union-attr]

    def test_typeddict_query_required_keys(self) -> None:
        @get("/items")
        async def handler(query: RequiredQueryParams) -> dict:
            return {}

        app = Litestar(route_handlers=[handler])
        parameters = app.openapi_schema.paths["/items"].get.parameters  # type: ignore[index, union-attr]
        assert parameters is not None

        params = {p.name: p for p in parameters if isinstance(p, Parameter)}

        assert params["page"].required is True
        assert params["search"].required is True

    def test_typeddict_query_optional_keys(self) -> None:
        @get("/items")
        async def handler(query: QueryParams) -> dict:
            return {}

        app = Litestar(route_handlers=[handler])
        parameters = app.openapi_schema.paths["/items"].get.parameters  # type: ignore[index, union-attr]
        assert parameters is not None

        params = {p.name: p for p in parameters if isinstance(p, Parameter)}

        # QueryParams uses total=False, so all keys are optional
        assert params["page"].required is False
        assert params["search"].required is False


class TestTypedDictHeaderParameters:
    """Test that a TypedDict annotation on the ``headers`` reserved kwarg
    generates individual header parameters in the OpenAPI schema."""

    def test_typeddict_headers_generates_parameters(self) -> None:
        @get("/items")
        async def handler(headers: HeaderParams) -> dict:
            return {}

        app = Litestar(route_handlers=[handler])
        parameters = app.openapi_schema.paths["/items"].get.parameters  # type: ignore[index, union-attr]
        assert parameters is not None

        params = [p for p in parameters if isinstance(p, Parameter)]
        param_names = {p.name for p in params}
        assert "x_api_key" in param_names
        assert "x_request_id" in param_names

    def test_typeddict_headers_param_type_is_header(self) -> None:
        @get("/items")
        async def handler(headers: HeaderParams) -> dict:
            return {}

        app = Litestar(route_handlers=[handler])
        parameters = app.openapi_schema.paths["/items"].get.parameters  # type: ignore[index, union-attr]
        assert parameters is not None

        params = {p.name: p for p in parameters if isinstance(p, Parameter)}

        assert params["x_api_key"].param_in == ParamType.HEADER
        assert params["x_request_id"].param_in == ParamType.HEADER


class TestTypedDictCookieParameters:
    """Test that a TypedDict annotation on the ``cookies`` reserved kwarg
    generates individual cookie parameters in the OpenAPI schema."""

    def test_typeddict_cookies_generates_parameters(self) -> None:
        @get("/items")
        async def handler(cookies: CookieParams) -> dict:
            return {}

        app = Litestar(route_handlers=[handler])
        parameters = app.openapi_schema.paths["/items"].get.parameters  # type: ignore[index, union-attr]
        assert parameters is not None

        params = [p for p in parameters if isinstance(p, Parameter)]
        param_names = {p.name for p in params}
        assert "session_id" in param_names
        assert "tracking_id" in param_names

    def test_typeddict_cookies_param_type_is_cookie(self) -> None:
        @get("/items")
        async def handler(cookies: CookieParams) -> dict:
            return {}

        app = Litestar(route_handlers=[handler])
        parameters = app.openapi_schema.paths["/items"].get.parameters  # type: ignore[index, union-attr]
        assert parameters is not None

        params = {p.name: p for p in parameters if isinstance(p, Parameter)}

        assert params["session_id"].param_in == ParamType.COOKIE
        assert params["tracking_id"].param_in == ParamType.COOKIE


class TestUntypedReservedKwargsUnchanged:
    """Verify that untyped/dict-typed reserved kwargs don't produce OpenAPI
    parameters — preserving backward compatibility."""

    def test_dict_query_no_parameters(self) -> None:
        @get("/items")
        async def handler(query: dict) -> dict:
            return {}

        app = Litestar(route_handlers=[handler])
        params = app.openapi_schema.paths["/items"].get.parameters  # type: ignore[index, union-attr]
        assert params is None

    def test_plain_dict_str_str_no_parameters(self) -> None:
        @get("/items")
        async def handler(query: dict[str, str]) -> dict:
            return {}

        app = Litestar(route_handlers=[handler])
        params = app.openapi_schema.paths["/items"].get.parameters  # type: ignore[index, union-attr]
        assert params is None


class TestOpenAPIJSONOutput:
    """Integration test that verifies the generated OpenAPI JSON output
    via the test client, matching real-world usage."""

    def test_typeddict_query_in_openapi_json(self) -> None:
        @get("/items")
        async def handler(query: QueryParams) -> dict:
            return {}

        with create_test_client(
            route_handlers=[handler],
            openapi_config=OpenAPIConfig(title="Test API", version="1.0.0"),
        ) as client:
            response = client.get("/schema/openapi.json")
            assert response.status_code == 200
            data = response.json()

            parameters = data["paths"]["/items"]["get"]["parameters"]
            param_names = {p["name"] for p in parameters}
            assert "page" in param_names
            assert "search" in param_names

            page_param = next(p for p in parameters if p["name"] == "page")
            assert page_param["in"] == "query"
            assert page_param["schema"]["type"] == "integer"
