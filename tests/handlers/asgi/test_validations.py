import pytest
from starlette.types import Receive, Scope, Send

from starlite import ImproperlyConfiguredException, asgi
from starlite.testing import create_test_client


def test_asgi_handler_validation() -> None:
    async def fn_without_scope_arg(receive: Receive, send: Send) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        asgi(path="/")(fn_without_scope_arg)

    async def fn_without_receive_arg(scope: Scope, send: Send) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        asgi(path="/")(fn_without_receive_arg)

    async def fn_without_send_arg(scope: Scope, receive: Receive) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        asgi(path="/")(fn_without_send_arg)

    async def fn_with_return_annotation(scope: Scope, receive: Receive, send: Send) -> dict:
        return dict()

    with pytest.raises(ImproperlyConfiguredException):
        asgi(path="/")(fn_with_return_annotation)

    asgi_handler_with_no_fn = asgi(path="/")

    with pytest.raises(ImproperlyConfiguredException):
        create_test_client(route_handlers=asgi_handler_with_no_fn)

    def sync_fn(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    with pytest.raises(ImproperlyConfiguredException):
        asgi(path="/")(sync_fn)
