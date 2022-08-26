from typing import Any

import pytest
from pydantic_openapi_schema.v3_1_0 import Components
from pydantic_openapi_schema.v3_1_0.security_scheme import SecurityScheme

from starlite import HTTPRouteHandler, OpenAPIConfig, Starlite, get


@pytest.fixture()
def public_route() -> HTTPRouteHandler:
    @get("/handler")
    def _handler() -> Any:
        ...

    return _handler


@pytest.fixture()
def protected_route() -> HTTPRouteHandler:
    @get("/protected", security=[{"BearerToken": []}])
    def _handler() -> Any:
        ...

    return _handler


def test_schema_without_security_property(public_route: HTTPRouteHandler) -> None:
    app = Starlite(route_handlers=[public_route])
    schema = app.openapi_schema

    assert schema
    assert schema.components is None


def test_schema_with_security_scheme_defined(public_route: HTTPRouteHandler) -> None:
    app = Starlite(
        route_handlers=[public_route],
        openapi_config=OpenAPIConfig(
            title="test app",
            version="0.0.1",
            components=Components(
                securitySchemes={
                    "BearerToken": SecurityScheme(
                        type="http",
                        scheme="bearer",
                    )
                },
            ),
            security=[{"BearerToken": []}],
        ),
    )
    schema = app.openapi_schema
    assert schema
    schema_dict = schema.dict()

    schema_components = schema_dict.get("components", {})
    assert "securitySchemes" in schema_components

    securitySchemes = schema_components.get("securitySchemes", {})
    assert securitySchemes == {
        "BearerToken": {
            "type": "http",
            "description": None,
            "name": None,
            "security_scheme_in": None,
            "scheme": "bearer",
            "bearerFormat": None,
            "flows": None,
            "openIdConnectUrl": None,
        }
    }

    assert schema_dict.get("security", []) == [{"BearerToken": []}]


def test_schema_with_route_security_overriden(protected_route: HTTPRouteHandler) -> None:
    app = Starlite(
        route_handlers=[protected_route],
        openapi_config=OpenAPIConfig(
            title="test app",
            version="0.0.1",
            components=Components(
                securitySchemes={
                    "BearerToken": SecurityScheme(
                        type="http",
                        scheme="bearer",
                    )
                },
            ),
        ),
    )
    schema = app.openapi_schema
    assert schema
    schema_dict = schema.dict()

    route = schema_dict["paths"]["/protected"]["get"]
    assert route.get("security", None) == [{"BearerToken": []}]
