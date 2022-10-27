from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from starlette.status import HTTP_201_CREATED, HTTP_500_INTERNAL_SERVER_ERROR

from starlite import (
    HttpMethod,
    Request,
    Response,
    WebSocket,
    get,
    post,
    route,
    websocket,
)
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from starlite.middleware.session.base import BaseBackendConfig


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
            request.set_session({"username": "moishezuchmir"})
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


def test_use_of_custom_response_serializer_with_http_handler(session_backend_config: "BaseBackendConfig") -> None:
    class Obj:
        inner: str

    class MyResponse(Response):
        @staticmethod
        def serializer(value: Any) -> Union[Dict[str, Any], str]:
            if isinstance(value, Obj):
                return value.inner
            raise TypeError()

    @post("/create-session")
    def create_session_handler(request: Request) -> None:
        obj = Obj()
        obj.inner = "123Jeronimo"
        request.set_session({"value": obj})

    with create_test_client(
        route_handlers=[create_session_handler],
        middleware=[session_backend_config.middleware],
        response_class=MyResponse,
    ) as client:
        response = client.post("/create-session")
        assert response.status_code == HTTP_201_CREATED


async def test_use_of_custom_response_serializer_with_websocket_handler(
    session_backend_config: "BaseBackendConfig",
) -> None:
    class Obj:
        inner: str

    class MyResponse(Response):
        @staticmethod
        def serializer(value: Any) -> Union[Dict[str, Any], str]:
            if isinstance(value, Obj):
                return value.inner
            raise TypeError()

    @websocket("/create-session")
    async def create_session_handler(socket: WebSocket) -> None:
        await socket.accept()
        obj = Obj()
        obj.inner = "123Jeronimo"
        socket.set_session({"value": obj})
        await socket.send_json({"has_session": True})
        await socket.close()

    with create_test_client(
        route_handlers=[create_session_handler],
        middleware=[session_backend_config.middleware],
        response_class=MyResponse,
    ).websocket_connect("/create-session") as ws:
        data = ws.receive_json()
        assert data == {"has_session": True}


def get_session_installed(request: Request) -> Dict[str, bool]:
    return {"has_session": "session" in request.scope}


def test_middleware_exclude_pattern(memory_session_backend_config) -> None:
    memory_session_backend_config.exclude = ["north", "south"]

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
        middleware=[memory_session_backend_config.middleware],
    ) as client:
        response = client.get("/north")
        assert response.json() == {"has_session": False}

        response = client.get("/south")
        assert response.json() == {"has_session": False}

        response = client.get("/west")
        assert response.json() == {"has_session": True}


def test_middleware_exclude_flag(memory_session_backend_config) -> None:
    @get("/north")
    def north_handler(request: Request) -> Dict[str, bool]:
        return get_session_installed(request)

    @get("/south", skip_session=True)
    def south_handler(request: Request) -> Dict[str, bool]:
        return get_session_installed(request)

    with create_test_client(
        route_handlers=[north_handler, south_handler],
        middleware=[memory_session_backend_config.middleware],
    ) as client:
        response = client.get("/north")
        assert response.json() == {"has_session": True}

        response = client.get("/south")
        assert response.json() == {"has_session": False}


def test_middleware_exclude_custom_key(memory_session_backend_config) -> None:
    memory_session_backend_config.exclude_opt_key = "my_exclude_key"

    @get("/north")
    def north_handler(request: Request) -> Dict[str, bool]:
        return get_session_installed(request)

    @get("/south", my_exclude_key=True)
    def south_handler(request: Request) -> Dict[str, bool]:
        return get_session_installed(request)

    with create_test_client(
        route_handlers=[north_handler, south_handler],
        middleware=[memory_session_backend_config.middleware],
    ) as client:
        response = client.get("/north")
        assert response.json() == {"has_session": True}

        response = client.get("/south")
        assert response.json() == {"has_session": False}
