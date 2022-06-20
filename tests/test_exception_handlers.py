from typing import Type

import pytest
from starlette.status import HTTP_400_BAD_REQUEST

from starlite import (
    Controller,
    InternalServerException,
    MediaType,
    NotFoundException,
    Request,
    Response,
    Router,
    ServiceUnavailableException,
    ValidationException,
    create_test_client,
    get,
)
from starlite.types import ExceptionHandler


@pytest.mark.parametrize(
    ["exc_to_raise", "expected_layer"],
    [
        (ValidationException, "router"),
        (InternalServerException, "controller"),
        (ServiceUnavailableException, "handler"),
        (NotFoundException, "handler"),
    ],
)
def test_exception_handling(exc_to_raise: Exception, expected_layer: str) -> None:
    caller = {"name": ""}

    def create_named_handler(caller_name: str, expected_exception: Type[Exception]) -> ExceptionHandler:
        def handler(req: Request, exc: Exception) -> Response:
            assert isinstance(exc, expected_exception)
            assert isinstance(req, Request)
            caller["name"] = caller_name
            return Response(
                media_type=MediaType.JSON,
                content={},
                status_code=HTTP_400_BAD_REQUEST,
            )

        return handler

    class ControllerWithHandler(Controller):
        path = "/test"
        exception_handlers = {
            InternalServerException: create_named_handler("controller", InternalServerException),
            ServiceUnavailableException: create_named_handler("controller", ServiceUnavailableException),
        }

        @get(
            "/",
            exception_handlers={
                ServiceUnavailableException: create_named_handler("handler", ServiceUnavailableException),
                NotFoundException: create_named_handler("handler", NotFoundException),
            },
        )
        def my_handler(self) -> None:
            raise exc_to_raise

    my_router = Router(
        path="/base",
        route_handlers=[ControllerWithHandler],
        exception_handlers={
            InternalServerException: create_named_handler("router", InternalServerException),
            ValidationException: create_named_handler("router", ValidationException),
        },
    )

    with create_test_client(route_handlers=[my_router]) as client:
        client.get("/base/test/")
        assert caller["name"] == expected_layer
