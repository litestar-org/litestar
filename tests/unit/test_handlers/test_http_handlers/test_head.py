from pathlib import Path

import pytest

from litestar import HttpMethod, Litestar, head
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response.file import ASGIFileResponse, File
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client


def test_head_decorator() -> None:
    @head("/")
    def handler() -> None:
        return

    with create_test_client(handler) as client:
        response = client.head("/")
        assert response.status_code == HTTP_200_OK


def test_head_decorator_raises_validation_error_if_body_is_declared() -> None:
    with pytest.raises(ImproperlyConfiguredException):

        @head("/")
        def handler() -> dict:
            return {}

        handler.on_registration(Litestar())


def test_head_decorator_raises_validation_error_if_method_is_passed() -> None:
    with pytest.raises(ImproperlyConfiguredException):

        @head("/", http_method=HttpMethod.HEAD)
        def handler() -> None:
            return

        handler.on_registration(Litestar())


def test_head_decorator_does_not_raise_for_file_response() -> None:
    @head("/")
    def handler() -> "File":
        return File("test_to_response.py")

    Litestar(route_handlers=[handler])

    handler.on_registration(Litestar())


def test_head_decorator_does_not_raise_for_asgi_file_response() -> None:
    @head("/")
    def handler() -> ASGIFileResponse:
        return ASGIFileResponse(file_path=Path("test_head.py"))

    Litestar(route_handlers=[handler])

    handler.on_registration(Litestar())
