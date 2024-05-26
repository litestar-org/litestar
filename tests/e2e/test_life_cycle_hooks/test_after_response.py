from unittest.mock import MagicMock, call

import pytest

from litestar import Controller, Request, Router, get
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client


@pytest.mark.parametrize("sync", [True, False])
@pytest.mark.parametrize("layer", ["app", "router", "controller", "handler"])
def test_after_response_resolution(layer: str, sync: bool) -> None:
    mock = MagicMock()

    if sync:

        def handler(_: Request) -> None:  # pyright: ignore
            mock(layer)

    else:

        async def handler(_: Request) -> None:  # type: ignore[misc]
            mock(layer)

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
        assert all(c == call(layer) for c in mock.call_args_list)
