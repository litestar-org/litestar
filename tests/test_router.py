import pytest

from starlite import Controller, HttpMethod, get, patch, post
from starlite import route as route_decorator
from starlite.routing import Router


class MyController(Controller):
    path = "/test"

    @post()
    def post_method(self):
        pass

    @get()
    def get_method(self):
        pass

    @get(path="/{id:int}")
    def get_by_id_method(self):
        pass


@pytest.mark.parametrize("controller", [MyController, MyController()])
def test_register_with_controller_class(controller):
    router = Router(path="/base", route_handlers=[MyController])
    assert len(router.routes) == 2
    for route in router.routes:
        if len(route.methods) == 2:
            assert sorted(route.methods) == sorted(["GET", "HEAD"])
            assert route.path == "/base/test/{id:int}"
        else:
            assert sorted(route.methods) == sorted(["GET", "POST", "HEAD"])
            assert route.path == "/base/test"


def test_register_with_router_instance():
    top_level_router = Router(path="/top-level", route_handlers=[MyController])
    base_router = Router(path="/base", route_handlers=[top_level_router])

    assert len(base_router.routes) == 2
    for route in base_router.routes:
        if len(route.methods) == 2:
            assert sorted(route.methods) == sorted(["GET", "HEAD"])
            assert route.path == "/base/top-level/test/{id:int}"
        else:
            assert sorted(route.methods) == sorted(["GET", "POST", "HEAD"])
            assert route.path == "/base/top-level/test"


def test_register_with_route_handler_functions():
    @route_decorator(path="/first", http_method=[HttpMethod.GET, HttpMethod.POST])
    def first_route_handler():
        pass

    @get(path="/second")
    def second_route_handler():
        pass

    @patch(path="/first")
    def third_route_handler():
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
