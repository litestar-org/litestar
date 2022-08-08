import pytest
from starlette import status

from starlite import delete, get, patch, post, put, websocket
from starlite.config import CSRFConfig
from starlite.connection import WebSocket
from starlite.testing import create_test_client


@get(path="/")
def get_handler() -> None:
    pass


@post(path="/")
def post_handler() -> None:
    pass


@put(path="/")
def put_handler() -> None:
    pass


@delete(path="/")
def delete_handler() -> None:
    pass


@patch(path="/")
def patch_handler() -> None:
    pass


@pytest.fixture()
def csrf_config() -> CSRFConfig:
    return CSRFConfig(secret="secret")


def test_csrf_successful_flow(csrf_config: CSRFConfig) -> None:
    client = create_test_client(route_handlers=[get_handler, post_handler], csrf_config=csrf_config)

    response = client.get("/")

    csrf_token = response.cookies.get("csrftoken")  # type: ignore[no-untyped-call]
    assert csrf_token is not None

    set_cookie_header = response.headers.get("set-cookie")
    assert set_cookie_header is not None
    assert set_cookie_header.split("; ") == [
        f"csrftoken={csrf_token}",
        "Path=/",
        "SameSite=Lax",
    ]

    response = client.post("/", headers={"x-csrftoken": csrf_token})
    assert response.status_code, status.HTTP_201_CREATED


@pytest.mark.parametrize(
    "method",
    ["POST", "PUT", "DELETE", "PATCH"],
)
def test_unsafe_method_fails_without_csrf_header(method: str, csrf_config: CSRFConfig) -> None:
    client = create_test_client(
        route_handlers=[get_handler, post_handler, put_handler, delete_handler, patch_handler], csrf_config=csrf_config
    )

    response = client.get("/")

    csrf_token = response.cookies.get("csrftoken")  # type: ignore[no-untyped-call]
    assert csrf_token is not None

    response = client.request(method, "/")

    assert response.status_code, status.HTTP_403_FORBIDDEN
    assert response.text, "CSRF token verification failed"


def test_invalid_csrf_token(csrf_config: CSRFConfig) -> None:
    client = create_test_client(route_handlers=[get_handler, post_handler], csrf_config=csrf_config)
    response = client.get("/")

    csrf_token = response.cookies.get("csrftoken")  # type: ignore[no-untyped-call]
    assert csrf_token is not None

    response = client.post("/", headers={"x-csrftoken": csrf_token + "invalid"})

    assert response.status_code, status.HTTP_403_FORBIDDEN
    assert response.text, "CSRF token verification failed"


def test_csrf_token_too_short(csrf_config: CSRFConfig) -> None:
    client = create_test_client(route_handlers=[get_handler, post_handler], csrf_config=csrf_config)
    response = client.get("/")

    assert "csrftoken" in response.cookies

    response = client.post("/", headers={"x-csrftoken": "too-short"})

    assert response.status_code, status.HTTP_403_FORBIDDEN
    assert response.text, "CSRF token verification failed"


def test_websocket_ignored(csrf_config: CSRFConfig) -> None:
    @websocket(path="/")
    async def websocket_handler(socket: WebSocket) -> None:
        await socket.accept()
        await socket.send_json({"data": "123"})
        await socket.close()

    client = create_test_client(route_handlers=[websocket_handler], csrf_config=csrf_config)
    with client.websocket_connect("/") as ws:
        response = ws.receive_json()
        assert response is not None


def test_custom_csrf_config() -> None:
    csrf_config = CSRFConfig(
        secret="secret",
        cookie_name="custom-csrftoken",
        cookie_path="/custom",
        header_name="x-custom-csrftoken",
        cookie_secure=True,
        cookie_httponly=True,
        cookie_samesite="None",
        cookie_domain="test.com",
    )

    client = create_test_client(
        base_url="http://test.com", route_handlers=[get_handler, post_handler], csrf_config=csrf_config
    )

    response = client.get("/")
    csrf_token = response.cookies.get("custom-csrftoken")  # type: ignore[no-untyped-call]
    assert csrf_token is not None

    set_cookie_header = response.headers.get("set-cookie")
    assert set_cookie_header is not None
    assert set_cookie_header.split("; ") == [
        f"custom-csrftoken={csrf_token}",
        "Domain=test.com",
        "HttpOnly",
        "Path=/custom",
        "SameSite=None",
        "Secure",
    ]

    response = client.post("/", headers={"x-custom-csrftoken": csrf_token})
    assert response.status_code, status.HTTP_201_CREATED
