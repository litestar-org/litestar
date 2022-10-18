import html
from os import urandom
from pathlib import Path
from typing import Any, Optional

import pytest
from bs4 import BeautifulSoup
from starlette import status

from starlite import (
    Body,
    CSRFConfig,
    MediaType,
    RequestEncodingType,
    Template,
    TemplateConfig,
    WebSocket,
    delete,
    get,
    patch,
    post,
    put,
    websocket,
)
from starlite.status_codes import HTTP_200_OK, HTTP_201_CREATED
from starlite.template.jinja import JinjaTemplateEngine
from starlite.template.mako import MakoTemplateEngine
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


@pytest.mark.parametrize(
    "engine, template",
    (
        (JinjaTemplateEngine, "{{csrf_input}}"),
        (MakoTemplateEngine, "${csrf_input}"),
    ),
)
def test_csrf_form_parsing(engine: Any, template: str, template_dir: Path) -> None:
    @get(path="/", media_type=MediaType.HTML)
    def handler() -> Template:
        return Template(name="abc.html")

    @post("/")
    def form_handler(data: dict = Body(media_type=RequestEncodingType.URL_ENCODED)) -> dict:
        return data

    with create_test_client(
        route_handlers=[handler, form_handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=engine,
        ),
        csrf_config=CSRFConfig(secret=str(urandom(10))),
    ) as client:
        url = str(client.base_url) + "/"
        Path(template_dir / "abc.html").write_text(
            f'<html><body><div><form action="{url}" method="post">{template}</form></div></body></html>'
        )
        _ = client.get("/")
        response = client.get("/")
        html_soup = BeautifulSoup(html.unescape(response.text), features="html.parser")
        data = {"_csrf_token": html_soup.body.div.form.input.attrs.get("value")}
        response = client.post("/", data=data)
        assert response.status_code == HTTP_201_CREATED
        assert response.json() == data
