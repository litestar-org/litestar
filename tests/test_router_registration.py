import pytest

from starlite import (
    Controller,
    HttpMethod,
    Router,
    Starlite,
    WebSocket,
    get,
    patch,
    post,
    put,
    websocket,
)
from starlite import route as route_decorator
from starlite.exceptions import ImproperlyConfiguredException


class MyController(Controller):
    path = "/test"

    @post(include_in_schema=False)
    def post_method(self) -> None:
        pass

    @get()
    def get_method(self) -> None:
        pass

    @get(path="/{id:int}")
    def get_by_id_method(self) -> None:
        pass

    @websocket(path="/socket")
    async def ws(self, socket: WebSocket) -> None:
        pass


def test_register_with_controller_class() -> None:
    router = Router(path="/base", route_handlers=[MyController])
    assert len(router.routes) == 3
    for route in router.routes:
        if len(route.methods) == 2:
            assert sorted(route.methods) == sorted(["GET", "OPTIONS"])
            assert route.path == "/base/test/{id:int}"
        elif len(route.methods) == 3:
            assert sorted(route.methods) == sorted(["GET", "POST", "OPTIONS"])
            assert route.path == "/base/test"


def test_register_controller_on_different_routers() -> None:
    first_router = Router(path="/first", route_handlers=[MyController])
    second_router = Router(path="/second", route_handlers=[MyController])
    third_router = Router(path="/third", route_handlers=[MyController])

    assert first_router.routes[0].route_handlers[0].owner.owner is first_router  # type: ignore
    assert second_router.routes[0].route_handlers[0].owner.owner is second_router  # type: ignore
    assert third_router.routes[0].route_handlers[0].owner.owner is third_router  # type: ignore


def test_register_with_router_instance() -> None:
    top_level_router = Router(path="/top-level", route_handlers=[MyController])
    base_router = Router(path="/base", route_handlers=[top_level_router])

    assert len(base_router.routes) == 3
    for route in base_router.routes:
        if len(route.methods) == 2:
            assert sorted(route.methods) == sorted(["GET", "OPTIONS"])
            assert route.path == "/base/top-level/test/{id:int}"
        elif len(route.methods) == 3:
            assert sorted(route.methods) == sorted(["GET", "POST", "OPTIONS"])
            assert route.path == "/base/top-level/test"


def test_register_with_route_handler_functions() -> None:
    @route_decorator(path="/first", http_method=[HttpMethod.GET, HttpMethod.POST], status_code=200)
    def first_route_handler() -> None:
        pass

    @get(path="/second")
    def second_route_handler() -> None:
        pass

    @patch(path="/first")
    def third_route_handler() -> None:
        pass

    router = Router(path="/base", route_handlers=[first_route_handler, second_route_handler, third_route_handler])
    assert len(router.routes) == 2
    for route in router.routes:
        if len(route.methods) == 2:
            assert sorted(route.methods) == sorted(["GET", "OPTIONS"])
            assert route.path == "/base/second"
        else:
            assert sorted(route.methods) == sorted(["GET", "POST", "PATCH", "OPTIONS"])
            assert route.path == "/base/first"
            assert route.path == "/base/first"


def test_register_validation_wrong_class() -> None:
    class MyCustomClass:
        @get(path="/first")
        def first_route_handler(self) -> None:
            pass

        @get(path="/first")
        def second_route_handler(self) -> None:
            pass

    with pytest.raises(ImproperlyConfiguredException):
        Router(path="/base", route_handlers=[MyCustomClass])


def test_register_already_registered_router() -> None:
    first_router = Router(path="/first", route_handlers=[])
    Router(path="/second", route_handlers=[first_router])

    with pytest.raises(ImproperlyConfiguredException):
        Router(path="/third", route_handlers=[first_router])


def test_register_router_on_itself() -> None:
    router = Router(path="/first", route_handlers=[])

    with pytest.raises(ImproperlyConfiguredException):
        router.register(router)


def test_route_handler_method_view() -> None:
    @get(path="/root")
    def handler() -> None:
        ...

    def _handler() -> None:
        ...

    put_handler = put("/modify")(_handler)
    post_handler = post("/send")(_handler)

    first_router = Router(path="/first", route_handlers=[MyController, post_handler, put_handler])
    second_router = Router(path="/second", route_handlers=[MyController, post_handler, put_handler])

    app = Starlite(route_handlers=[first_router, second_router, handler])

    assert app.route_handler_method_view[str(handler)] == ["/root"]
    assert app.route_handler_method_view[str(MyController.get_method)] == [
        "/first/test",
        "/second/test",
    ]

    assert app.route_handler_method_view[str(MyController.ws)] == [
        "/first/test/socket",
        "/second/test/socket",
    ]
    assert app.route_handler_method_view[str(put_handler)] == [
        "/first/send",
        "/first/modify",
        "/second/send",
        "/second/modify",
    ]
    assert app.route_handler_method_view[str(post_handler)] == [
        "/first/send",
        "/first/modify",
        "/second/send",
        "/second/modify",
    ]
