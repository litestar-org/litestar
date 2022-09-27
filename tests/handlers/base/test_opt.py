from typing import TYPE_CHECKING, Callable

import pytest

from starlite import asgi, delete, get, patch, post, put, websocket

if TYPE_CHECKING:
    from starlite import WebSocket
    from starlite.types import Receive, RouteHandlerType, Scope, Send


def regular_handler() -> None:
    ...


async def asgi_handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
    ...


async def socket_handler(socket: "WebSocket") -> None:
    ...


@pytest.mark.parametrize(
    "decorator, handler",
    [
        (get, regular_handler),
        (post, regular_handler),
        (delete, regular_handler),
        (put, regular_handler),
        (patch, regular_handler),
        (asgi, asgi_handler),
        (websocket, socket_handler),
    ],
)
def test_opt_settings(decorator: "RouteHandlerType", handler: Callable) -> None:
    base_opt = {"base": 1, "kwarg_value": 0}
    result = decorator("/", opt=base_opt, kwarg_value=2)(handler)  # type: ignore
    assert result.opt == {"base": 1, "kwarg_value": 2}
