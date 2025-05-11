from dataclasses import dataclass

import pytest

from litestar import Litestar, get, post
from litestar.dto import DTOData
from litestar.exceptions import ImproperlyConfiguredException
from litestar.middleware import ASGIMiddleware
from litestar.middleware.constraints import ConstraintViolationError, MiddlewareConstraints
from litestar.types import ASGIApp, Receive, Scope, Send


def test_dto_data_annotation_with_no_resolved_dto() -> None:
    @dataclass
    class Model:
        """Example dataclass model."""

        hello: str

    @post("/")
    async def async_hello_world(data: DTOData[Model]) -> Model:
        """Route Handler that outputs hello world."""
        return data.create_instance()

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[async_hello_world])


def test_check_middleware_constraints() -> None:
    class MiddlewareOne(ASGIMiddleware):
        async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
            pass

    class MiddlewareTwo(ASGIMiddleware):
        constraints = MiddlewareConstraints(after=(MiddlewareOne,))

        async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
            pass

    @get("/", middleware=[MiddlewareOne()])
    async def handler() -> None:
        pass

    with pytest.raises(
        ConstraintViolationError,
        match=r"All instances of .*MiddlewareTwo' must come after any instance of .*MiddlewareOne'. "
        r"\(Found instance of .*MiddlewareTwo' at index 0, instance of .*MiddlewareOne' at index 1\)",
    ):
        Litestar([handler], middleware=[MiddlewareTwo()])
