from typing import Optional

import pytest
from starlette import status
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from starlite import CSRFConfig, WebSocket, delete, get, patch, post, put, websocket
from starlite.testing import create_test_client


@get(path="/")
def get_handler() -> None:
    return None


@post(path="/")
def post_handler() -> None:
    return None


@put(path="/")
def put_handler() -> None:
    return None


@delete(path="/")
def delete_handler() -> None:
    return None


@patch(path="/")
def patch_handler() -> None:
    return None


def test_csrf_successful_flow() -> None:
    with create_test_client(
        route_handlers=[get_handler, post_handler], csrf_config=CSRFConfig(secret="secret")
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        csrf_token: Optional[str] = response.cookies.get("csrftoken")
        assert csrf_token is not None

        set_cookie_header = response.headers.get("set-cookie")
        assert set_cookie_header is not None
        assert set_cookie_header.split("; ") == [
            f"csrftoken={csrf_token}",
            "Path=/",
            "SameSite=lax",
        ]

        response = client.post("/", headers={"x-csrftoken": csrf_token})
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize(
    "method",
    ["POST", "PUT", "DELETE", "PATCH"],
)
def test_unsafe_method_fails_without_csrf_header(method: str) -> None:
    with create_test_client(
        route_handlers=[get_handler, post_handler, put_handler, delete_handler, patch_handler],
        csrf_config=CSRFConfig(secret="secret"),
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        csrf_token: Optional[str] = response.cookies.get("csrftoken")
        assert csrf_token is not None

        response = client.request(method, "/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "CSRF token verification failed", "status_code": 403}


def test_invalid_csrf_token() -> None:
    with create_test_client(
        route_handlers=[get_handler, post_handler], csrf_config=CSRFConfig(secret="secret")
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        csrf_token: Optional[str] = response.cookies.get("csrftoken")
        assert csrf_token is not None

        response = client.post("/", headers={"x-csrftoken": csrf_token + "invalid"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "CSRF token verification failed", "status_code": 403}


def test_csrf_token_too_short() -> None:
    with create_test_client(
        route_handlers=[get_handler, post_handler], csrf_config=CSRFConfig(secret="secret")
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        assert "csrftoken" in response.cookies

        response = client.post("/", headers={"x-csrftoken": "too-short"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "CSRF token verification failed", "status_code": 403}


def test_websocket_ignored() -> None:
    @websocket(path="/")
    async def websocket_handler(socket: WebSocket) -> None:
        await socket.accept()
        await socket.send_json({"data": "123"})
        await socket.close()

    with create_test_client(
        route_handlers=[websocket_handler], csrf_config=CSRFConfig(secret="secret")
    ) as client, client.websocket_connect("/") as ws:
        response = ws.receive_json()
        assert response is not None


def test_custom_csrf_config() -> None:
    with create_test_client(
        base_url="http://test.com",
        route_handlers=[get_handler, post_handler],
        csrf_config=CSRFConfig(
            secret="secret",
            cookie_name="custom-csrftoken",
            header_name="x-custom-csrftoken",
        ),
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        csrf_token: Optional[str] = response.cookies.get("custom-csrftoken")
        assert csrf_token is not None

        set_cookie_header = response.headers.get("set-cookie")
        assert set_cookie_header is not None
        assert set_cookie_header.split("; ") == [
            f"custom-csrftoken={csrf_token}",
            "Path=/",
            "SameSite=lax",
        ]

        response = client.post("/", headers={"x-custom-csrftoken": csrf_token})
        assert response.status_code == HTTP_201_CREATED
