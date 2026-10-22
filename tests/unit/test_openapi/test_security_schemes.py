from typing import TYPE_CHECKING, Any

import pytest

from litestar import Controller, Litestar, Router, get
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Components
from litestar.openapi.spec.security_scheme import SecurityScheme

if TYPE_CHECKING:
    from litestar.handlers.http_handlers import HTTPRouteHandler


@pytest.fixture()
def public_route() -> "HTTPRouteHandler":
    @get("/handler")
    def _handler() -> Any: ...

    return _handler


@pytest.fixture()
def protected_route() -> "HTTPRouteHandler":
    @get("/protected", security=[{"BearerToken": []}])
    def _handler() -> Any: ...

    return _handler


def test_schema_without_security_property(public_route: "HTTPRouteHandler") -> None:
    app = Litestar(route_handlers=[public_route])
    schema = app.openapi_schema

    assert schema
    assert schema.components
    assert not schema.components.security_schemes


def test_schema_with_security_scheme_defined(public_route: "HTTPRouteHandler") -> None:
    app = Litestar(
        route_handlers=[public_route],
        openapi_config=OpenAPIConfig(
            title="test app",
            version="0.0.1",
            components=Components(
                security_schemes={
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
    schema_dict = schema.to_schema()

    schema_components = schema_dict.get("components", {})
    assert "securitySchemes" in schema_components

    assert schema_components.get("securitySchemes", {}) == {
        "BearerToken": {
            "type": "http",
            "scheme": "bearer",
        }
    }

    assert schema_dict.get("security", []) == [{"BearerToken": []}]


def test_schema_with_route_security_overridden(protected_route: "HTTPRouteHandler") -> None:
    app = Litestar(
        route_handlers=[protected_route],
        openapi_config=OpenAPIConfig(
            title="test app",
            version="0.0.1",
            components=Components(
                security_schemes={
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
    schema_dict = schema.to_schema()

    route = schema_dict["paths"]["/protected"]["get"]
    assert route.get("security", None) == [{"BearerToken": []}]


def test_layered_security_declaration() -> None:
    class MyController(Controller):
        path = "/controller"
        security = [{"controllerToken": []}]

        @get("", security=[{"handlerToken": []}])
        def my_handler(self) -> None: ...

    router = Router("/router", route_handlers=[MyController], security=[{"routerToken": []}])

    app = Litestar(
        route_handlers=[router],
        security=[{"appToken": []}],
        openapi_config=OpenAPIConfig(
            title="test app",
            version="0.0.1",
            components=Components(
                security_schemes={
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
    assert app.openapi_schema
    assert app.openapi_schema.components
    security_schemes = app.openapi_schema.components.security_schemes
    assert security_schemes

    assert list(security_schemes.keys()) == [
        "handlerToken",
        "controllerToken",
        "routerToken",
        "appToken",
    ]

    assert app.openapi_schema
    paths = app.openapi_schema.paths
    assert paths
    assert paths["/router/controller"].get
    assert paths["/router/controller"].get.security == [
        {"appToken": []},
        {"routerToken": []},
        {"controllerToken": []},
        {"handlerToken": []},
    ]


def test_schema_without_any_security_omits_operation_security(public_route: "HTTPRouteHandler") -> None:
    """When no layer declares ``security``, the operation should omit the field entirely, so it falls back to
    whatever global ``security`` is declared on the OpenAPI document, rather than being treated as an explicit
    opt-out.
    """
    app = Litestar(
        route_handlers=[public_route],
        openapi_config=OpenAPIConfig(title="test app", version="0.0.1", security=[{"BearerToken": []}]),
    )
    schema_dict = app.openapi_schema.to_schema()

    assert schema_dict["paths"]["/handler"]["get"].get("security") is None
    assert schema_dict.get("security") == [{"BearerToken": []}]


def test_schema_with_explicit_empty_route_security_opts_out() -> None:
    """A route handler explicitly declaring ``security=[]`` (with no security declared on any ownership layer)
    should be documented as requiring no security, instead of falling back to the document-level default.
    """

    @get("/public", security=[])
    def _handler() -> Any: ...

    app = Litestar(
        route_handlers=[_handler],
        openapi_config=OpenAPIConfig(title="test app", version="0.0.1", security=[{"BearerToken": []}]),
    )
    schema_dict = app.openapi_schema.to_schema()

    assert schema_dict["paths"]["/public"]["get"].get("security") == []
    assert schema_dict.get("security") == [{"BearerToken": []}]


def test_explicit_empty_route_security_does_not_cancel_ownership_layer_security() -> None:
    """A route handler cannot use ``security=[]`` to cancel security requirements declared on an ownership layer
    above it (router/controller/app) - security requirements are additive, and there's no override semantic for
    individual layers.
    """

    @get("/opt-out", security=[])
    def _handler() -> Any: ...

    router = Router("/router", route_handlers=[_handler], security=[{"routerToken": []}])
    app = Litestar(route_handlers=[router])
    schema_dict = app.openapi_schema.to_schema()

    assert schema_dict["paths"]["/router/opt-out"]["get"].get("security") == [{"routerToken": []}]
