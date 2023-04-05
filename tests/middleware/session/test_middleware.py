from typing import TYPE_CHECKING, Dict, Optional

from starlite import HttpMethod, Request, get, post, route
from starlite.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from starlite.testing import create_test_client
from starlite.types import Empty

if TYPE_CHECKING:
    from starlite.middleware.session.base import BaseBackendConfig
    from starlite.middleware.session.server_side import ServerSideSessionConfig


def test_session_middleware_not_installed_raises() -> None:
    @get("/test")
    def handler(request: Request) -> None:
        if request.session:
            raise AssertionError("this line should not be hit")

    with create_test_client(handler) as client:
        response = client.get("/test")
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "'session' is not defined in scope, install a SessionMiddleware to set it"


def test_integration(session_backend_config: "BaseBackendConfig") -> None:
    @route("/session", http_method=[HttpMethod.GET, HttpMethod.POST, HttpMethod.DELETE])
    def session_handler(request: Request) -> Optional[Dict[str, bool]]:
        if request.method == HttpMethod.GET:
            return {"has_session": request.session != {}}

        if request.method == HttpMethod.DELETE:
            request.clear_session()
        else:
            request.session["username"] = "moishezuchmir"
        return None

    with create_test_client(route_handlers=[session_handler], middleware=[session_backend_config.middleware]) as client:
        response = client.get("/session")
        assert response.json() == {"has_session": False}

        client.post("/session")

        response = client.get("/session")
        assert response.json() == {"has_session": True}

        client.delete("/session")

        response = client.get("/session")
        assert response.json() == {"has_session": False}

        client.post("/session")

        response = client.get("/session")
        assert response.json() == {"has_session": True}


def test_set_empty(session_backend_config: "BaseBackendConfig") -> None:
    @post("/create-session")
    def create_session_handler(request: Request) -> None:
        request.set_session({"foo": "bar"})

    @post("/empty-session")
    def empty_session_handler(request: Request) -> None:
        request.set_session(Empty)

    with create_test_client(
        route_handlers=[create_session_handler, empty_session_handler],
        middleware=[session_backend_config.middleware],
        session_config=session_backend_config,
    ) as client:
        client.post("/create-session")
        client.post("/empty-session")
        assert not client.get_session_data()


def get_session_installed(request: Request) -> Dict[str, bool]:
    return {"has_session": "session" in request.scope}


def test_middleware_exclude_pattern(session_backend_config_memory: "ServerSideSessionConfig") -> None:
    session_backend_config_memory.exclude = ["north", "south"]

    @get("/north")
    def north_handler(request: Request) -> Dict[str, bool]:
        return get_session_installed(request)

    @get("/south")
    def south_handler(request: Request) -> Dict[str, bool]:
        return get_session_installed(request)

    @get("/west")
    def west_handler(request: Request) -> Dict[str, bool]:
        return get_session_installed(request)

    with create_test_client(
        route_handlers=[north_handler, south_handler, west_handler],
        middleware=[session_backend_config_memory.middleware],
    ) as client:
        response = client.get("/north")
        assert response.json() == {"has_session": False}

        response = client.get("/south")
        assert response.json() == {"has_session": False}

        response = client.get("/west")
        assert response.json() == {"has_session": True}


def test_middleware_exclude_flag(session_backend_config_memory: "ServerSideSessionConfig") -> None:
    @get("/north")
    def north_handler(request: Request) -> Dict[str, bool]:
        return get_session_installed(request)

    @get("/south", skip_session=True)
    def south_handler(request: Request) -> Dict[str, bool]:
        return get_session_installed(request)

    with create_test_client(
        route_handlers=[north_handler, south_handler],
        middleware=[session_backend_config_memory.middleware],
    ) as client:
        response = client.get("/north")
        assert response.json() == {"has_session": True}

        response = client.get("/south")
        assert response.json() == {"has_session": False}


def test_middleware_exclude_custom_key(session_backend_config_memory: "ServerSideSessionConfig") -> None:
    session_backend_config_memory.exclude_opt_key = "my_exclude_key"

    @get("/north")
    def north_handler(request: Request) -> Dict[str, bool]:
        return get_session_installed(request)

    @get("/south", my_exclude_key=True)
    def south_handler(request: Request) -> Dict[str, bool]:
        return get_session_installed(request)

    with create_test_client(
        route_handlers=[north_handler, south_handler],
        middleware=[session_backend_config_memory.middleware],
    ) as client:
        response = client.get("/north")
        assert response.json() == {"has_session": True}

        response = client.get("/south")
        assert response.json() == {"has_session": False}
