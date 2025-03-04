import pytest

from litestar import Controller, Litestar, Router, post
from litestar.exceptions import ImproperlyConfiguredException
from litestar.types import Empty


def test_resolve_request_max_body_size() -> None:
    @post("/1")
    def router_handler() -> None:
        pass

    @post("/2")
    def app_handler() -> None:
        pass

    class MyController(Controller):
        request_max_body_size = 2

        @post("/3")
        def controller_handler(self) -> None:
            pass

    router = Router("/", route_handlers=[router_handler], request_max_body_size=1)
    app = Litestar(route_handlers=[app_handler, router, MyController], request_max_body_size=3)
    assert router_handler.resolve_request_max_body_size() == 1
    assert app_handler.resolve_request_max_body_size() == 3
    assert (
        next(r for r in app.routes if r.path == "/3").route_handler_map["POST"][0].resolve_request_max_body_size() == 2  # type: ignore[union-attr]
    )


def test_resolve_request_max_body_size_none() -> None:
    @post("/1", request_max_body_size=None)
    def router_handler() -> None:
        pass

    Litestar([router_handler])
    assert router_handler.resolve_request_max_body_size() is None


def test_resolve_request_max_body_size_app_default() -> None:
    @post("/")
    def router_handler() -> None:
        pass

    app = Litestar(route_handlers=[router_handler])

    assert router_handler.resolve_request_max_body_size() == app.request_max_body_size == 10_000_000


def test_resolve_request_max_body_size_empty_on_all_layers_raises() -> None:
    @post("/")
    def handler_one() -> None:
        pass

    Litestar([handler_one], request_max_body_size=Empty)  # type: ignore[arg-type]
    with pytest.raises(ImproperlyConfiguredException):
        handler_one.resolve_request_max_body_size()

    @post("/")
    def handler_two() -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        handler_two.resolve_request_max_body_size()
