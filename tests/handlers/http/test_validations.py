from pathlib import Path
from typing import Dict

import pytest

from starlite import HttpMethod, MediaType, WebSocket, delete, get, route
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.handlers.http_handlers import HTTPRouteHandler
from starlite.response_containers import File, Redirect
from starlite.status_codes import (
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
    with pytest.raises(ImproperlyConfiguredException):

        @get(path="/")
        def method_with_no_annotation():  # type: ignore
            pass

        method_with_no_annotation.on_startup()

    with pytest.raises(ImproperlyConfiguredException):

        @delete(path="/")
        def method_with_no_content() -> Dict[str, str]:
            return {}

        method_with_no_content.on_startup()

    with pytest.raises(ImproperlyConfiguredException):

        @get(path="/", status_code=HTTP_304_NOT_MODIFIED)
        def method_with_not_modified() -> Dict[str, str]:
            return {}

        method_with_not_modified.on_startup()

    with pytest.raises(ImproperlyConfiguredException):

        @get(path="/", status_code=HTTP_100_CONTINUE)
        def method_with_status_lower_than_200() -> Dict[str, str]:
            return {}

        method_with_status_lower_than_200.on_startup()

    @get(path="/", status_code=HTTP_307_TEMPORARY_REDIRECT)
    def redirect_method() -> Redirect:
        return Redirect("/test")

    redirect_method.on_startup()

    @get(path="/")
    def file_method() -> File:
        return File(path=Path("."), filename="test_validations.py")

    file_method.on_startup()

    assert file_method.media_type == MediaType.TEXT

    with pytest.raises(ImproperlyConfiguredException):

        @get(path="/test")
        def test_function_1(socket: WebSocket) -> None:
            return None

        test_function_1.on_startup()

    with pytest.raises(ImproperlyConfiguredException):

        @get("/person")
        def test_function_2(self, data: Person) -> None:  # type: ignore
            return None

        test_function_2.on_startup()
