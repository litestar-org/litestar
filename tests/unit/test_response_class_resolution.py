from typing import Type, Union

import pytest

from litestar import Controller, HttpMethod, Litestar, Response, Router, get

RouterResponse: Type[Response] = type("RouterResponse", (Response,), {})
ControllerResponse: Type[Response] = type("ControllerResponse", (Response,), {})
AppResponse: Type[Response] = type("AppResponse", (Response,), {})
HandlerResponse: Type[Response] = type("HandlerResponse", (Response,), {})


@pytest.mark.parametrize(
    "handler_response_class, controller_response_class, router_response_class, app_response_class, expected",
    (
        (HandlerResponse, ControllerResponse, RouterResponse, AppResponse, HandlerResponse),
        (None, ControllerResponse, RouterResponse, AppResponse, ControllerResponse),
        (None, None, RouterResponse, AppResponse, RouterResponse),
        (None, None, None, AppResponse, AppResponse),
        (None, None, None, None, Response),
    ),
    ids=(
        "Custom class for all layers",
        "Custom class for all above handler layer",
        "Custom class for all above controller layer",
        "Custom class for all above router layer",
        "No custom class for layers",
    ),
)
def test_response_class_resolution_of_layers(
    handler_response_class: Union[Type[Response], None],
    controller_response_class: Union[Type[Response], None],
    router_response_class: Union[Type[Response], None],
    app_response_class: Union[Type[Response], None],
    expected: Type[Response],
) -> None:
    class MyController(Controller):
        @get()
        def handler(self) -> None:
            pass

    if controller_response_class:
        MyController.response_class = ControllerResponse

    router = Router(path="/", route_handlers=[MyController])

    if router_response_class:
        router.response_class = router_response_class

    app = Litestar(route_handlers=[router])

    if app_response_class:
        app.response_class = app_response_class

    route_handler, _ = app.routes[0].route_handler_map[HttpMethod.GET]  # type: ignore

    if handler_response_class:
        route_handler.response_class = handler_response_class

    response_class = route_handler.resolve_response_class()
    assert response_class is expected
