from __future__ import annotations

import pytest

from starlite import Controller, Router, Starlite, post
from starlite.types import Empty

from . import ConcreteDTO


@pytest.mark.parametrize("layer", ["app", "router", "controller", "handler"])
def test_data_dto_layered_resolution(layer: str) -> None:
    class MyController(Controller):
        data_dto = ConcreteDTO if layer == "controller" else Empty

        @post(data_dto=ConcreteDTO if layer == "handler" else Empty)
        def my_post_handler(self) -> None:
            ...

    router = Router(path="/", route_handlers=[MyController], data_dto=ConcreteDTO if layer == "router" else Empty)
    app = Starlite(route_handlers=[router], data_dto=ConcreteDTO if layer == "app" else Empty, openapi_config=None)
    assert app.route_handler_method_map["/"]["POST"].resolve_data_dto() is ConcreteDTO  # type:ignore[union-attr]
