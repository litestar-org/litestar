import pytest

from starlite import (
    Controller,
    HttpMethod,
    ImproperlyConfiguredException,
    WebSocket,
    get,
    patch,
    post,
)
from starlite import route as route_decorator
from starlite import websocket
from starlite.routing import Router


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
    def ws(self, socket: WebSocket) -> None:
        pass


def test_register_with_controller_class():
    router = Router(path="/base", route_handlers=[MyController])
    assert len(router.routes) == 3
    for route in router.routes:
        if len(route.methods) == 2:
            assert sorted(route.methods) == sorted(["GET", "HEAD"])
            assert route.path == "/base/test/{id:int}"
        elif len(route.methods) == 3:
            assert sorted(route.methods) == sorted(["GET", "POST", "HEAD"])
            assert route.path == "/base/test"


def test_register_with_router_instance():
    top_level_router = Router(path="/top-level", route_handlers=[MyController])
    base_router = Router(path="/base", route_handlers=[top_level_router])

    assert len(base_router.routes) == 3
    for route in base_router.routes:
        if len(route.methods) == 2:
            assert sorted(route.methods) == sorted(["GET", "HEAD"])
            assert route.path == "/base/top-level/test/{id:int}"
        elif len(route.methods) == 3:
            assert sorted(route.methods) == sorted(["GET", "POST", "HEAD"])
            assert route.path == "/base/top-level/test"


def test_register_with_route_handler_functions():
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
            assert sorted(route.methods) == sorted(["GET", "HEAD"])
            assert route.path == "/base/second"
        else:
            assert sorted(route.methods) == sorted(["GET", "POST", "PATCH", "HEAD"])
            assert route.path == "/base/first"
            assert route.path == "/base/first"


def test_register_validation_duplicate_handlers_for_same_route_and_method():
    @get(path="/first")
    def first_route_handler() -> None:
        pass

    @get(path="/first")
    def second_route_handler() -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Router(path="/base", route_handlers=[first_route_handler, second_route_handler])


def test_register_validation_wrong_class():
    class MyCustomClass:
        @get(path="/first")
        def first_route_handler(self) -> None:
            pass

        @get(path="/first")
        def second_route_handler(self) -> None:
            pass

    with pytest.raises(ImproperlyConfiguredException):
        Router(path="/base", route_handlers=[MyCustomClass])


def test_register_already_registered_router():
    first_router = Router(path="/first", route_handlers=[])
    Router(path="/second", route_handlers=[first_router])

    with pytest.raises(ImproperlyConfiguredException):
        Router(path="/third", route_handlers=[first_router])


def test_register_router_on_itself():
    router = Router(path="/first", route_handlers=[])

    with pytest.raises(ImproperlyConfiguredException):
        router.register(router)


def test_deprecates_properties_correctly():
    router = Router(path="/first", route_handlers=[])

    def my_fn() -> None:
        pass

    with pytest.raises(AttributeError):
        router.route(my_fn)

    with pytest.raises(AttributeError):
        router.add_route(my_fn)
