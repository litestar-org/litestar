from typing import Any, Dict, Optional

import pytest
from pydantic_openapi_schema.v3_1_0 import Components, SecurityScheme

from starlite import (
    ASGIConnection,
    BaseRouteHandler,
    OpenAPIConfig,
    Provide,
    create_test_client,
    get,
)
from starlite.middleware.session.memory_backend import MemoryBackendConfig
from starlite.security import SessionAuth
from starlite.status_codes import HTTP_200_OK


def retrieve_user_handler(_: Dict[str, Any], __: ASGIConnection) -> Any:
    pass


def test_abstract_security_config_sets_guards() -> None:
    async def guard(_: "ASGIConnection", __: BaseRouteHandler) -> None:
        pass

    security_config = SessionAuth[Any](
        retrieve_user_handler=retrieve_user_handler, session_backend_config=MemoryBackendConfig(), guards=[guard]
    )

    with create_test_client([], on_app_init=[security_config.on_app_init]) as client:
        assert client.app.guards


def test_abstract_security_config_sets_dependencies() -> None:
    security_config = SessionAuth[Any](
        retrieve_user_handler=retrieve_user_handler,
        session_backend_config=MemoryBackendConfig(),
        dependencies={"value": Provide(lambda: 13)},
    )

    with create_test_client([], on_app_init=[security_config.on_app_init]) as client:
        assert client.app.dependencies.get("value")


def test_abstract_security_config_registers_route_handlers() -> None:
    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    security_config = SessionAuth[Any](
        retrieve_user_handler=retrieve_user_handler,
        exclude=["/"],
        session_backend_config=MemoryBackendConfig(),
        route_handlers=[handler],
    )

    with create_test_client([], on_app_init=[security_config.on_app_init]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"hello": "world"}


@pytest.mark.parametrize(
    "openapi_config, expected",
    (
        (None, None),
        (
            OpenAPIConfig(title="Starlite API", version="1.0.0", components=None),
            {
                "securitySchemes": {
                    "sessionCookie": {
                        "type": "apiKey",
                        "description": "Session cookie authentication.",
                        "name": "Set-Cookie",
                        "security_scheme_in": "cookie",
                    }
                }
            },
        ),
        (
            OpenAPIConfig(
                title="Starlite API",
                version="1.0.0",
                components=[
                    Components(
                        securitySchemes={
                            "app": SecurityScheme(
                                type="http",
                                name="test",
                                security_scheme_in="cookie",
                                description="test.",
                            )
                        }
                    )
                ],
            ),
            {
                "securitySchemes": {
                    "app": {"type": "http", "description": "test.", "name": "test", "security_scheme_in": "cookie"},
                    "sessionCookie": {
                        "type": "apiKey",
                        "description": "Session cookie authentication.",
                        "name": "Set-Cookie",
                        "security_scheme_in": "cookie",
                    },
                }
            },
        ),
        (
            OpenAPIConfig(
                title="Starlite API",
                version="1.0.0",
                components=Components(
                    securitySchemes={
                        "app": SecurityScheme(
                            type="http",
                            name="test",
                            security_scheme_in="cookie",
                            description="test.",
                        )
                    }
                ),
            ),
            {
                "securitySchemes": {
                    "sessionCookie": {
                        "type": "apiKey",
                        "description": "Session cookie authentication.",
                        "name": "Set-Cookie",
                        "security_scheme_in": "cookie",
                    },
                    "app": {"type": "http", "description": "test.", "name": "test", "security_scheme_in": "cookie"},
                }
            },
        ),
    ),
)
def test_abstract_security_config_setting_openapi_components(
    openapi_config: Optional[OpenAPIConfig], expected: dict
) -> None:
    security_config = SessionAuth[Any](
        retrieve_user_handler=retrieve_user_handler, exclude=["/"], session_backend_config=MemoryBackendConfig()
    )

    with create_test_client([], on_app_init=[security_config.on_app_init], openapi_config=openapi_config) as client:
        if openapi_config is not None:
            assert client.app.openapi_config
            assert client.app.openapi_config.components
            assert client.app.openapi_config.components.dict(exclude_none=True) == expected  # type: ignore
        else:
            assert not client.app.openapi_config


@pytest.mark.parametrize(
    "openapi_config, expected",
    (
        (None, None),
        (OpenAPIConfig(title="Starlite API", version="1.0.0", security=None), [{"sessionCookie": []}]),
        (
            OpenAPIConfig(title="Starlite API", version="1.0.0", security=[{"app": ["a", "b", "c"]}]),
            [{"app": ["a", "b", "c"]}, {"sessionCookie": []}],
        ),
    ),
)
def test_abstract_security_config_setting_openapi_security_requirements(
    openapi_config: Optional[OpenAPIConfig], expected: list
) -> None:
    security_config = SessionAuth[Any](
        retrieve_user_handler=retrieve_user_handler, exclude=["/"], session_backend_config=MemoryBackendConfig()
    )

    with create_test_client([], on_app_init=[security_config.on_app_init], openapi_config=openapi_config) as client:
        if openapi_config is not None:
            assert client.app.openapi_config
            assert client.app.openapi_config.security
            assert client.app.openapi_config.security == expected
        else:
            assert not client.app.openapi_config
