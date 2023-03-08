from __future__ import annotations

import pytest

from starlite import Controller, Router, Starlite, post
from starlite.types import Empty, EmptyType

from . import ExampleDTO, Model


@pytest.mark.parametrize("layer", ["app", "router", "controller", "handler"])
def test_dto_layer_resolution(layer: str) -> None:
    data_dto = ExampleDTO[Model]
    ret_dto = ExampleDTO[Model]

    def get_data(layer_name: str) -> type[ExampleDTO] | EmptyType:
        return data_dto if layer == layer_name else Empty

    def get_ret(layer_name: str) -> type[ExampleDTO] | EmptyType:
        return ret_dto if layer == layer_name else Empty

    class MyController(Controller):
        data_dto = get_data("controller")
        return_dto = get_ret("controller")

        @post(data_dto=get_data("handler"), return_dto=get_ret("handler"))
        def my_post_handler(self, data: Model) -> Model:
            return data

    router = Router(path="/", route_handlers=[MyController], data_dto=get_data("router"), return_dto=get_ret("router"))
    app = Starlite(route_handlers=[router], data_dto=get_data("app"), return_dto=get_ret("app"))
    assert app.route_handler_method_map["/"]["POST"].resolve_data_dto() is data_dto  # type:ignore[union-attr]
    assert app.route_handler_method_map["/"]["POST"].resolve_return_dto() is ret_dto  # type:ignore[union-attr]
