from typing import Callable, Union

import pytest

from litestar import Litestar, Router, delete, get, head, patch, post, put
from litestar.exceptions.http_exceptions import ImproperlyConfiguredException
from litestar.handlers.http_handlers import HTTPRouteHandler
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Components
from litestar.openapi.spec.security_scheme import SecurityScheme


@pytest.fixture()
def openapi_config_with_optional_security_scheme() -> OpenAPIConfig:
    return OpenAPIConfig(
        title="test app",
        version="0.0.1",
        components=Components(
            security_schemes={
                "MyGlobalToken": SecurityScheme(
                    type="http",
                    scheme="bearer",
                ),
                "MyRouterToken": SecurityScheme(
                    type="http",
                    scheme="bearer",
                ),
                "MyRouteToken": SecurityScheme(
                    type="http",
                    scheme="bearer",
                ),
            },
        ),
    )


@pytest.fixture()
def openapi_config_with_global_requirement(
    openapi_config_with_optional_security_scheme: OpenAPIConfig,
) -> OpenAPIConfig:
    openapi_config_with_optional_security_scheme.security = [{"MyGlobalToken": []}]
    return openapi_config_with_optional_security_scheme


@pytest.fixture(params=[get, post, put, patch, head, delete])
def sample_handlers(
    request: pytest.FixtureRequest,
) -> list[Union[HTTPRouteHandler, Router]]:
    method_decorator: Callable[..., Callable[..., HTTPRouteHandler]] = request.param

    @method_decorator("/route_security_not_specified")
    def route_security_not_specified() -> None: ...

    @method_decorator("/route_with_security", security=[{"MyRouteToken": []}])
    def route_with_security() -> None: ...

    @method_decorator("/route_with_security_override", security_override=[{"MyRouteToken": []}])
    def route_with_security_override() -> None: ...

    @method_decorator("/route_with_empty_security", security=[])
    def route_with_empty_security() -> None: ...

    @method_decorator("/route_with_empty_security_override", security_override=[])
    def route_with_empty_security_override() -> None: ...

    sample_routes = [
        route_security_not_specified,
        route_with_security,
        route_with_security_override,
        route_with_empty_security,
        route_with_empty_security_override,
    ]

    return [
        *sample_routes,
        Router(
            "/router_security_not_specified",
            route_handlers=sample_routes,
        ),
        Router(
            "/router_with_security",
            security=[{"MyRouterToken": []}],
            route_handlers=sample_routes,
        ),
        Router(
            "/router_with_security_override",
            security_override=[{"MyRouterToken": []}],
            route_handlers=sample_routes,
        ),
        Router(
            "/router_with_empty_security",
            security=[],
            route_handlers=sample_routes,
        ),
        Router(
            "/router_with_empty_security_override",
            security_override=[{"MyRouterToken": []}],
            route_handlers=sample_routes,
        ),
    ]


def test_app_schema_without_global_security_property(
    request: pytest.FixtureRequest,
    openapi_config_with_optional_security_scheme: OpenAPIConfig,
    sample_handlers: list[Union[HTTPRouteHandler, Router]],
) -> None:
    app = Litestar(
        openapi_config=openapi_config_with_optional_security_scheme,
        route_handlers=sample_handlers,
    )
    schema = app.openapi_schema

    assert schema
    assert schema.components
    assert schema.components.security_schemes == {
        "MyGlobalToken": SecurityScheme(
            type="http",
            scheme="bearer",
        ),
        "MyRouterToken": SecurityScheme(
            type="http",
            scheme="bearer",
        ),
        "MyRouteToken": SecurityScheme(
            type="http",
            scheme="bearer",
        ),
    }

    assert schema.security is None

    method = request.node.callspec.params["sample_handlers"].__name__
    schema_dict = schema.to_schema()
    paths = schema_dict["paths"]

    # No router
    assert "security" not in paths["/route_security_not_specified"][method]
    assert paths["/route_with_security"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/route_with_security_override"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/route_with_empty_security"][method]["security"] == ()
    assert paths["/route_with_empty_security_override"][method]["security"] == ()

    # router_security_not_specified
    assert "security" not in paths["/router_security_not_specified/route_security_not_specified"][method]
    assert paths["/router_security_not_specified/route_with_security"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/router_security_not_specified/route_with_security_override"][method]["security"] == (
        {"MyRouteToken": []},
    )
    assert paths["/router_security_not_specified/route_with_empty_security"][method]["security"] == ()
    assert paths["/router_security_not_specified/route_with_empty_security_override"][method]["security"] == ()

    # router_with_security
    assert paths["/router_with_security/route_security_not_specified"][method]["security"] == ({"MyRouterToken": []},)
    assert paths["/router_with_security/route_with_security"][method]["security"] == (
        {"MyRouteToken": []},
        {"MyRouterToken": []},
    )
    assert paths["/router_with_security/route_with_security_override"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/router_with_security/route_with_empty_security"][method]["security"] == ({"MyRouterToken": []},)
    assert paths["/router_with_security/route_with_empty_security_override"][method]["security"] == ()

    # router_with_security_override
    assert paths["/router_with_security_override/route_security_not_specified"][method]["security"] == (
        {"MyRouterToken": []},
    )
    assert paths["/router_with_security_override/route_with_security"][method]["security"] == (
        {"MyRouteToken": []},
        {"MyRouterToken": []},
    )
    assert paths["/router_with_security_override/route_with_security_override"][method]["security"] == (
        {"MyRouteToken": []},
    )
    assert paths["/router_with_security_override/route_with_empty_security"][method]["security"] == (
        {"MyRouterToken": []},
    )
    assert paths["/router_with_security_override/route_with_empty_security_override"][method]["security"] == ()

    # router_with_empty_security
    assert paths["/router_with_empty_security/route_security_not_specified"][method]["security"] == ()
    assert paths["/router_with_empty_security/route_with_security"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/router_with_empty_security/route_with_security_override"][method]["security"] == (
        {"MyRouteToken": []},
    )
    assert paths["/router_with_empty_security/route_with_empty_security"][method]["security"] == ()
    assert paths["/router_with_empty_security/route_with_empty_security_override"][method]["security"] == ()

    # router_with_empty_security_override
    assert paths["/router_with_empty_security/route_security_not_specified"][method]["security"] == ()
    assert paths["/router_with_empty_security/route_with_security"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/router_with_empty_security/route_with_security_override"][method]["security"] == (
        {"MyRouteToken": []},
    )
    assert paths["/router_with_empty_security/route_with_empty_security"][method]["security"] == ()
    assert paths["/router_with_empty_security/route_with_empty_security_override"][method]["security"] == ()


def test_app_schema_with_global_security_property(
    request: pytest.FixtureRequest,
    openapi_config_with_global_requirement: OpenAPIConfig,
    sample_handlers: list[Union[HTTPRouteHandler, Router]],
) -> None:
    app = Litestar(
        openapi_config=openapi_config_with_global_requirement,
        route_handlers=sample_handlers,
    )
    schema = app.openapi_schema

    assert schema
    assert schema.components
    assert schema.components.security_schemes == {
        "MyGlobalToken": SecurityScheme(
            type="http",
            scheme="bearer",
        ),
        "MyRouterToken": SecurityScheme(
            type="http",
            scheme="bearer",
        ),
        "MyRouteToken": SecurityScheme(
            type="http",
            scheme="bearer",
        ),
    }

    assert schema.security == [{"MyGlobalToken": []}]

    method = request.node.callspec.params["sample_handlers"].__name__
    schema_dict = schema.to_schema()
    paths = schema_dict["paths"]

    # No router
    assert "security" not in paths["/route_security_not_specified"][method]
    assert paths["/route_with_security"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/route_with_security_override"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/route_with_empty_security"][method]["security"] == ()
    assert paths["/route_with_empty_security_override"][method]["security"] == ()

    # router_security_not_specified
    assert "security" not in paths["/router_security_not_specified/route_security_not_specified"][method]
    assert paths["/router_security_not_specified/route_with_security"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/router_security_not_specified/route_with_security_override"][method]["security"] == (
        {"MyRouteToken": []},
    )
    assert paths["/router_security_not_specified/route_with_empty_security"][method]["security"] == ()
    assert paths["/router_security_not_specified/route_with_empty_security_override"][method]["security"] == ()

    # router_with_security
    assert paths["/router_with_security/route_security_not_specified"][method]["security"] == ({"MyRouterToken": []},)
    assert paths["/router_with_security/route_with_security"][method]["security"] == (
        {"MyRouteToken": []},
        {"MyRouterToken": []},
    )
    assert paths["/router_with_security/route_with_security_override"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/router_with_security/route_with_empty_security"][method]["security"] == ({"MyRouterToken": []},)
    assert paths["/router_with_security/route_with_empty_security_override"][method]["security"] == ()

    # router_with_security_override
    assert paths["/router_with_security_override/route_security_not_specified"][method]["security"] == (
        {"MyRouterToken": []},
    )
    assert paths["/router_with_security_override/route_with_security"][method]["security"] == (
        {"MyRouteToken": []},
        {"MyRouterToken": []},
    )
    assert paths["/router_with_security_override/route_with_security_override"][method]["security"] == (
        {"MyRouteToken": []},
    )
    assert paths["/router_with_security_override/route_with_empty_security"][method]["security"] == (
        {"MyRouterToken": []},
    )
    assert paths["/router_with_security_override/route_with_empty_security_override"][method]["security"] == ()

    # router_with_empty_security
    assert paths["/router_with_empty_security/route_security_not_specified"][method]["security"] == ()
    assert paths["/router_with_empty_security/route_with_security"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/router_with_empty_security/route_with_security_override"][method]["security"] == (
        {"MyRouteToken": []},
    )
    assert paths["/router_with_empty_security/route_with_empty_security"][method]["security"] == ()
    assert paths["/router_with_empty_security/route_with_empty_security_override"][method]["security"] == ()

    # router_with_empty_security_override
    assert paths["/router_with_empty_security/route_security_not_specified"][method]["security"] == ()
    assert paths["/router_with_empty_security/route_with_security"][method]["security"] == ({"MyRouteToken": []},)
    assert paths["/router_with_empty_security/route_with_security_override"][method]["security"] == (
        {"MyRouteToken": []},
    )
    assert paths["/router_with_empty_security/route_with_empty_security"][method]["security"] == ()
    assert paths["/router_with_empty_security/route_with_empty_security_override"][method]["security"] == ()


def test_improperly_configured_security_override() -> None:
    with pytest.raises(ImproperlyConfiguredException):

        @get(
            "/sample",
            security=[{"MyGlobalToken": []}],
            security_override=[{"MyRouteToken": []}],
        )
        def _invalid_route_handler() -> None: ...

    with pytest.raises(ImproperlyConfiguredException):

        @get("/sample")
        def sample_handler() -> None: ...

        Router(
            "/",
            security=[{"MyGlobalToken": []}],
            security_override=[{"MyRouteToken": []}],
            route_handlers=[sample_handler],
        )
