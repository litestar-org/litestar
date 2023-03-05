from typing import TYPE_CHECKING, Any, List

import pytest
from pydantic_openapi_schema.v3_1_0 import Components, SecurityRequirement
from pydantic_openapi_schema.v3_1_0.security_scheme import SecurityScheme

from starlite import Controller, Router, Starlite, get
from starlite.openapi.config import OpenAPIConfig

if TYPE_CHECKING:
    from starlite.handlers.http_handlers import HTTPRouteHandler


@pytest.fixture()
def public_route() -> "HTTPRouteHandler":
    @get("/handler")
    def _handler() -> Any:
        ...

    return _handler


@pytest.fixture()
def protected_route() -> "HTTPRouteHandler":
    @get("/protected", security=[{"BearerToken": []}])
    def _handler() -> Any:
        ...

    return _handler


def test_schema_without_security_property(public_route: "HTTPRouteHandler") -> None:
    app = Starlite(route_handlers=[public_route])
    schema = app.openapi_schema

    assert schema
    assert schema.components is None


def test_schema_with_security_scheme_defined(public_route: "HTTPRouteHandler") -> None:
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

    assert schema_components.get("securitySchemes", {}) == {
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


def test_schema_with_route_security_overridden(protected_route: "HTTPRouteHandler") -> None:
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


def test_layered_security_declaration() -> None:
    class MyController(Controller):
        path = "/controller"
        security: List[SecurityRequirement] = [{"controllerToken": []}]

        @get("", security=[{"handlerToken": []}])
        def my_handler(self) -> None:
            ...

    router = Router("/router", route_handlers=[MyController], security=[{"routerToken": []}])

    app = Starlite(
        route_handlers=[router],
        security=[{"appToken": []}],
        openapi_config=OpenAPIConfig(
            title="test app",
            version="0.0.1",
            components=Components(
                securitySchemes={
                    "handlerToken": SecurityScheme(
                        type="http",
                        scheme="bearer",
                    ),
                    "controllerToken": SecurityScheme(
                        type="http",
                        scheme="bearer",
                    ),
                    "routerToken": SecurityScheme(
                        type="http",
                        scheme="bearer",
                    ),
                    "appToken": SecurityScheme(
                        type="http",
                        scheme="bearer",
                    ),
                },
            ),
        ),
    )
    assert list(app.openapi_schema.components.securitySchemes.keys()) == [  # type: ignore
        "handlerToken",
        "controllerToken",
        "routerToken",
        "appToken",
    ]
    assert app.openapi_schema.paths["/router/controller"].get.security == [  # type: ignore
        {"appToken": []},
        {"routerToken": []},
        {"controllerToken": []},
        {"handlerToken": []},
    ]
