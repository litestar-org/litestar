from __future__ import annotations

import pytest

from starlite import Controller, Router, Starlite, post
from starlite.types import Empty, EmptyType

from . import ConcreteDTO


class ReturnDTO(ConcreteDTO):
    """Just a test"""


@pytest.mark.parametrize("layer", ["app", "router", "controller", "handler"])
def test_dto_layer_resolution(layer: str) -> None:
    def get_data(layer_name: str) -> type[ConcreteDTO] | EmptyType:
        return ConcreteDTO if layer == layer_name else Empty

    def get_ret(layer_name: str) -> type[ReturnDTO] | EmptyType:
        return ReturnDTO if layer == layer_name else Empty

    class MyController(Controller):
        data_dto = get_data("controller")
        return_dto = get_ret("controller")

        @post(data_dto=get_data("handler"), return_dto=get_ret("handler"))
        def my_post_handler(self) -> None:
            ...

    router = Router(path="/", route_handlers=[MyController], data_dto=get_data("router"), return_dto=get_ret("router"))
    app = Starlite(route_handlers=[router], data_dto=get_data("app"), return_dto=get_ret("app"))
    assert app.route_handler_method_map["/"]["POST"].resolve_data_dto() is ConcreteDTO  # type:ignore[union-attr]
    assert app.route_handler_method_map["/"]["POST"].resolve_return_dto() is ReturnDTO  # type:ignore[union-attr]
