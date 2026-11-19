import secrets
from typing import TYPE_CHECKING, Any

import pytest

from litestar import Controller, Litestar, Router, get
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Components
from litestar.openapi.spec.security_scheme import SecurityScheme
from litestar.security.jwt import JWTCookieAuth, OAuth2PasswordBearerAuth, Token
from tests.unit.test_openapi.utils import build_document

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
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


async def retrieve_user_handler(token: Token, connection: "ASGIConnection[Any, Any, Any, Any]") -> Any:
    return None


def test_jwt_cookie_auth_security_scheme() -> None:
    jwt_auth = JWTCookieAuth[Any](token_secret=secrets.token_hex(), retrieve_user_handler=retrieve_user_handler)

    document = build_document(app_kwargs={"on_app_init": [jwt_auth.on_app_init]})

    assert document["components"]["securitySchemes"] == {
        "BearerToken": {
            "type": "http",
            "description": "JWT cookie-based authentication and authorization.",
            "scheme": "Bearer",
            "bearerFormat": "JWT",
        }
    }
    assert document["security"] == [{"BearerToken": []}]


@pytest.mark.parametrize(
    "oauth_scopes, expected_scopes",
    [(None, {}), ({"read": "Read access"}, {"read": "Read access"})],
)
def test_oauth2_password_bearer_auth_security_scheme(
    oauth_scopes: dict[str, str] | None, expected_scopes: dict[str, str]
) -> None:
    jwt_auth = OAuth2PasswordBearerAuth[Any](
        token_url="/login",
        token_secret=secrets.token_hex(),
        retrieve_user_handler=retrieve_user_handler,
        oauth_scopes=oauth_scopes,
    )

    document = build_document(app_kwargs={"on_app_init": [jwt_auth.on_app_init]})

    assert document["components"]["securitySchemes"] == {
        "BearerToken": {
            "type": "oauth2",
            "description": "OAUTH2 password bearer authentication and authorization.",
            "flows": {"password": {"tokenUrl": "/login", "scopes": expected_scopes}},
        }
    }
    assert document["security"] == [{"BearerToken": []}]
