from pathlib import Path
from typing import Dict

import pytest

from litestar import HttpMethod, Litestar, WebSocket, delete, get, route
from litestar.exceptions import ImproperlyConfiguredException, ValidationException
from litestar.handlers.http_handlers import HTTPRouteHandler
from litestar.response import FileResponse, RedirectResponse
from litestar.status_codes import (
    HTTP_100_CONTINUE,
    HTTP_200_OK,
    HTTP_304_NOT_MODIFIED,
    HTTP_307_TEMPORARY_REDIRECT,
)
from tests import Person


def test_route_handler_validation_http_method() -> None:
    # doesn't raise for http methods
    for value in (*list(HttpMethod), *[x.upper() for x in list(HttpMethod)]):
        assert route(http_method=value)  # type: ignore

    # raises for invalid values
    with pytest.raises(ValidationException):
        HTTPRouteHandler(http_method="deleze")  # type: ignore

    # also when passing an empty list
    with pytest.raises(ImproperlyConfiguredException):
        route(http_method=[], status_code=HTTP_200_OK)

    # also when passing malformed tokens
    with pytest.raises(ValidationException):
        route(http_method=[HttpMethod.GET, "poft"], status_code=HTTP_200_OK)  # type: ignore


async def test_function_validation() -> None:
    Litestar()

    with pytest.raises(ImproperlyConfiguredException):

        @get(path="/")
        def method_with_no_annotation():  # type: ignore
            pass

        method_with_no_annotation.on_registration(Litestar())

    with pytest.raises(ImproperlyConfiguredException):

        @delete(path="/")
        def method_with_no_content() -> Dict[str, str]:
            return {}

        method_with_no_content.on_registration(Litestar())

    with pytest.raises(ImproperlyConfiguredException):

        @get(path="/", status_code=HTTP_304_NOT_MODIFIED)
        def method_with_not_modified() -> Dict[str, str]:
            return {}

        method_with_not_modified.on_registration(Litestar())

    with pytest.raises(ImproperlyConfiguredException):

        @get(path="/", status_code=HTTP_100_CONTINUE)
        def method_with_status_lower_than_200() -> Dict[str, str]:
            return {}

        method_with_status_lower_than_200.on_registration(Litestar())

    @get(path="/", status_code=HTTP_307_TEMPORARY_REDIRECT)
    def redirect_method() -> RedirectResponse:
        return RedirectResponse("/test")

    redirect_method.on_registration(Litestar())

    @get(path="/")
    def file_method() -> FileResponse:
        return FileResponse(path=Path("."), filename="test_validations.py")

    file_method.on_registration(Litestar())

    assert not file_method.media_type

    with pytest.raises(ImproperlyConfiguredException):

        @get(path="/test")
        def test_function_1(socket: WebSocket) -> None:
            return None

        test_function_1.on_registration(Litestar())

    with pytest.raises(ImproperlyConfiguredException):

        @get("/person")
        def test_function_2(self, data: Person) -> None:  # type: ignore
            return None

        test_function_2.on_registration(Litestar())
