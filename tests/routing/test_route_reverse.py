from typing import Type

import pytest

from starlite import (
    HTTPRouteHandler,
    Router,
    Starlite,
    ValidationException,
    delete,
    get,
    patch,
    post,
    put,
)


@pytest.mark.parametrize("decorator", [get, post, patch, put, delete])
def test_route_reverse(decorator: Type[HTTPRouteHandler]) -> None:
    @decorator("/path-one/{param:str}", name="handler-name")  # type: ignore
    def handler() -> None:
        return None

    @decorator("/path-two", name="handler-no-params")  # type: ignore
    def handler_no_params() -> None:
        return None

    @decorator("/multiple/{str_param:str}/params/{int_param:int}/", name="multiple-params-handler-name")  # type: ignore
    def handler2() -> None:
        return None

    router = Router("router-path/", route_handlers=[handler, handler_no_params])
    router_with_param = Router("router-with-param/{router_param:str}", route_handlers=[handler2])
    app = Starlite(route_handlers=[router, router_with_param])

    reversed_url_path = app.route_reverse("handler-name", param="param-value")
    assert reversed_url_path == "/router-path/path-one/param-value"

    reversed_url_path = app.route_reverse("handler-no-params")
    assert reversed_url_path == "/router-path/path-two"

    reversed_url_path = app.route_reverse(
        "multiple-params-handler-name", router_param="router", str_param="abc", int_param=123
    )
    assert reversed_url_path == "/router-with-param/router/multiple/abc/params/123"

    reversed_url_path = app.route_reverse("nonexistent-handler")
    assert reversed_url_path is None


def test_route_reverse_validation() -> None:
    @get("/abc/{param:int}", name="handler-name")
    def handler_one() -> None:
        pass

    @get("/def/{param:str}", name="another-handler-name")
    def handler_two() -> None:
        pass

    app = Starlite(route_handlers=[handler_one, handler_two])

    with pytest.raises(ValidationException):
        app.route_reverse("handler-name")

    with pytest.raises(ValidationException):
        app.route_reverse("handler-name", param="str")

    with pytest.raises(ValidationException):
        app.route_reverse("another-handler-name", param=1)
