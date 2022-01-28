import pytest
from pydantic import ValidationError
from starlette.status import HTTP_200_OK, HTTP_307_TEMPORARY_REDIRECT

from starlite import (
    File,
    HttpMethod,
    MediaType,
    Redirect,
    Response,
    WebSocket,
    get,
    route,
)
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.handlers import HTTPRouteHandler
from tests import Person


def test_route_handler_validation_http_method():
    # doesn't raise for http methods
    for value in [*list(HttpMethod), *list(map(lambda x: x.upper(), list(HttpMethod)))]:
        assert route(http_method=value)

    # raises for invalid values
    with pytest.raises(ValidationError):
        HTTPRouteHandler(http_method="deleze")

    with pytest.raises(ImproperlyConfiguredException):
        HTTPRouteHandler(http_method=None)

    # also when passing an empty list
    with pytest.raises(ImproperlyConfiguredException):
        route(http_method=[], status_code=HTTP_200_OK)

    # also when passing malformed tokens
    with pytest.raises(ValidationError):
        route(http_method=[HttpMethod.GET, "poft"], status_code=HTTP_200_OK)


def test_route_handler_validation_response_class():
    # doesn't raise when subclass of starlette response is passed
    class SpecialResponse(Response):
        pass

    assert HTTPRouteHandler(http_method=HttpMethod.GET, response_class=SpecialResponse)

    # raises otherwise
    with pytest.raises(ValidationError):
        HTTPRouteHandler(http_method=HttpMethod.GET, response_class=dict())


@pytest.mark.asyncio
async def test_function_validation():
    with pytest.raises(ValidationException):

        @get(path="/")
        def method_with_no_annotation():
            pass

    with pytest.raises(ValidationException):

        @get(path="/", status_code=HTTP_200_OK)
        def redirect_method_without_proper_status() -> Redirect:
            pass

    @get(path="/", status_code=HTTP_307_TEMPORARY_REDIRECT)
    def redirect_method() -> Redirect:
        return Redirect("/test")

    @get(path="/")
    def file_method() -> File:
        pass

    assert file_method.media_type == MediaType.TEXT

    with pytest.raises(ImproperlyConfiguredException):

        @get(path="/test")
        def test_function_1(socket: WebSocket) -> None:
            ...

    with pytest.raises(ImproperlyConfiguredException):

        @get("/person")
        def test_function_2(self, data: Person) -> None:
            ...
