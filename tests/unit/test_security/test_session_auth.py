from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

import msgspec
import pytest
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_401_UNAUTHORIZED,
)

from litestar import Litestar, Request, delete, get, post
from litestar.middleware.session.server_side import (
    ServerSideSessionBackend,
    ServerSideSessionConfig,
)
from litestar.params import FromPath, JSONBody
from litestar.security.session_auth import SessionAuth
from litestar.security.session_auth.middleware import SessionAuthMiddleware
from litestar.testing import create_test_client
from tests.models import User, UserFactory

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

user_instance = UserFactory.build()


def retrieve_user_handler(session_data: dict[str, Any], _: "ASGIConnection") -> Optional[User]:
    if session_data["id"] == str(user_instance.id):
        return User(**session_data)
    return None


def test_authentication(session_backend_config_memory: ServerSideSessionConfig) -> None:
    session_auth = SessionAuth[Any, ServerSideSessionBackend](
        retrieve_user_handler=retrieve_user_handler,
        exclude=["login"],
        session_backend_config=session_backend_config_memory,
    )

    @post("/login")
    def login_handler(request: "Request[Any, Any, Any]", data: JSONBody[User]) -> None:
        request.set_session(msgspec.to_builtins(data))

    @delete("/user/{user_id:str}")
    def delete_user_handler(request: "Request[User, Any, Any]") -> None:
        request.clear_session()

    @get("/user/{user_id:str}")
    def get_user_handler(request: "Request[User, Any, Any]") -> User:
        return request.user

    with create_test_client(
        route_handlers=[login_handler, delete_user_handler, get_user_handler],
        on_app_init=[session_auth.on_app_init],
    ) as client:
        response = client.get(f"user/{user_instance.id}")
        assert response.status_code == HTTP_401_UNAUTHORIZED, response.json()

        response = client.post("/login", json={"id": str(user_instance.id), "name": user_instance.name})
        assert response.status_code == HTTP_201_CREATED, response.json()

        response = client.get(f"user/{user_instance.id}")
        assert response.status_code == HTTP_200_OK, response.json()

        response = client.delete(f"user/{user_instance.id}")
        assert response.status_code == HTTP_204_NO_CONTENT, response.json()

        response = client.get(f"user/{user_instance.id}")
        assert response.status_code == HTTP_401_UNAUTHORIZED, response.json()

        response = client.post("/login", json={"id": str(uuid4()), "name": user_instance.name})
        assert response.status_code == HTTP_201_CREATED, response.json()

        response = client.get(f"user/{user_instance.id}")
        assert response.status_code == HTTP_401_UNAUTHORIZED, response.json()


def test_session_backend_exclusions_apply_under_session_auth(
    session_backend_config_memory: ServerSideSessionConfig,
) -> None:
    session_backend_config_memory.exclude = ["/excluded"]
    session_backend_config_memory.exclude_opt_key = "no_session"
    session_auth = SessionAuth[Any, ServerSideSessionBackend](
        retrieve_user_handler=retrieve_user_handler,
        exclude=["/excluded", "/opt-out"],
        session_backend_config=session_backend_config_memory,
    )

    @get("/excluded")
    def excluded_handler(request: Request) -> dict[str, bool]:
        return {"has_session": "session" in request.scope}

    @get("/opt-out", no_session=True)
    def opt_out_handler(request: Request) -> dict[str, bool]:
        return {"has_session": "session" in request.scope}

    with create_test_client(
        route_handlers=[excluded_handler, opt_out_handler], on_app_init=[session_auth.on_app_init]
    ) as client:
        assert client.get("/excluded").json() == {"has_session": False}
        assert client.get("/opt-out").json() == {"has_session": False}


@pytest.mark.parametrize(
    "exclude_kwargs, second_status",
    [
        ({"exclude": ["^/user/1$"]}, HTTP_401_UNAUTHORIZED),
        ({"exclude_path_pattern": [r"^/user/\{user_id:int\}$"]}, HTTP_200_OK),
    ],
    ids=["request_path", "handler_path"],
)
def test_session_auth_exclude_dynamic_path(
    session_backend_config_memory: ServerSideSessionConfig, exclude_kwargs: dict[str, Any], second_status: int
) -> None:
    session_auth = SessionAuth[Any, ServerSideSessionBackend](
        retrieve_user_handler=retrieve_user_handler,
        session_backend_config=session_backend_config_memory,
        **exclude_kwargs,
    )

    @get("/user/{user_id:int}")
    def handler(user_id: FromPath[int]) -> None:
        return None

    with create_test_client(route_handlers=[handler], on_app_init=[session_auth.on_app_init]) as client:
        assert client.get("/user/1").status_code == HTTP_200_OK
        assert client.get("/user/2").status_code == second_status


def test_unauthorized_response_clears_session_cookie(session_backend_config_memory: ServerSideSessionConfig) -> None:
    session_auth = SessionAuth[Any, ServerSideSessionBackend](
        retrieve_user_handler=retrieve_user_handler,
        exclude=["login"],
        session_backend_config=session_backend_config_memory,
    )

    @post("/login")
    def login_handler(request: "Request[Any, Any, Any]") -> None:
        request.set_session({"id": str(uuid4())})

    @get("/user")
    def get_user_handler(request: "Request[User, Any, Any]") -> User:
        return request.user

    with create_test_client(
        route_handlers=[login_handler, get_user_handler], on_app_init=[session_auth.on_app_init]
    ) as client:
        client.post("/login")
        assert client.cookies.get("session")
        response = client.get("/user")
        assert response.status_code == HTTP_401_UNAUTHORIZED
        assert "session=null" in response.headers["set-cookie"]


def test_middleware_accepts_sync_retrieve_user_handler(session_backend_config_memory: ServerSideSessionConfig) -> None:
    auth_middleware = SessionAuthMiddleware(
        exclude=["login"],
        exclude_http_methods=None,
        exclude_opt_key="exclude_from_auth",
        retrieve_user_handler=retrieve_user_handler,
        scopes=None,
    )

    @post("/login")
    def login_handler(request: "Request[Any, Any, Any]", data: JSONBody[User]) -> None:
        request.set_session(msgspec.to_builtins(data))

    @get("/user")
    def get_user_handler(request: "Request[User, Any, Any]") -> User:
        return request.user

    with create_test_client(
        route_handlers=[login_handler, get_user_handler],
        middleware=[session_backend_config_memory.middleware, auth_middleware],
    ) as client:
        client.post("/login", json={"id": str(user_instance.id), "name": user_instance.name})
        assert client.get("/user").status_code == HTTP_200_OK


def test_session_auth_openapi(session_backend_config_memory: "ServerSideSessionConfig") -> None:
    session_auth = SessionAuth[Any, ServerSideSessionBackend](
        retrieve_user_handler=retrieve_user_handler,
        session_backend_config=session_backend_config_memory,
    )
    app = Litestar(on_app_init=[session_auth.on_app_init])
    assert app.openapi_schema.to_schema() == {
        "openapi": "3.1.0",
        "info": {"title": "Litestar API", "version": "1.0.0"},
        "servers": [{"url": "/"}],
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {
                "sessionCookie": {
                    "type": "apiKey",
                    "description": "Session cookie authentication.",
                    "name": session_backend_config_memory.key,
                    "in": "cookie",
                }
            },
        },
        "security": [{"sessionCookie": []}],
    }
