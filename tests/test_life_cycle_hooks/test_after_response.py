from typing import TYPE_CHECKING, Dict

import pytest

from litestar import Controller, Request, Router, get
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client

state: Dict[str, str] = {}

if TYPE_CHECKING:
    from litestar.types import AfterResponseHookHandler


def create_sync_test_handler(msg: str) -> "AfterResponseHookHandler":
    def handler(_: Request) -> None:
        state["msg"] = msg

    return handler


def create_async_test_handler(msg: str) -> "AfterResponseHookHandler":
    async def handler(_: Request) -> None:
        state["msg"] = msg

    return handler


@pytest.mark.parametrize("layer", ["app", "router", "controller", "handler"])
def test_after_response_resolution(layer: str) -> None:
    for handler in (create_sync_test_handler(layer), create_async_test_handler(layer)):
        state.pop("msg", None)

        class MyController(Controller):
            path = "/controller"
            after_response = handler if layer == "controller" else None

            @get("/", after_response=handler if layer == "handler" else None)
            def my_handler(self) -> None:
                return None

        router = Router(
            path="/router", route_handlers=[MyController], after_response=handler if layer == "router" else None
        )

        with create_test_client(route_handlers=[router], after_response=handler if layer == "app" else None) as client:
            response = client.get("/router/controller/")
            assert response.status_code == HTTP_200_OK
            assert state["msg"] == layer
