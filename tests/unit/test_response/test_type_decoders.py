from typing import Any
from unittest import mock

from litestar import Controller, HttpMethod, Litestar, Router, get
from litestar.datastructures.url import URL

handler_decoder, router_decoder, controller_decoder, app_decoder = 4 * [(lambda t: t is URL, lambda t, v: URL(v))]


@mock.patch("litestar.app.Litestar._get_default_plugins", mock.Mock(return_value=[]))
def test_resolve_type_decoders() -> None:
    class MyController(Controller):
        type_decoders = [controller_decoder]

        @get("/", type_decoders=[handler_decoder])
        def handler(self) -> Any:
            ...

    router = Router("/router", type_decoders=[router_decoder], route_handlers=[MyController])
    app = Litestar([router], type_decoders=[app_decoder])
    route_handler = app.routes[0].route_handler_map[HttpMethod.GET][0]  # type: ignore
    decoders = route_handler.resolve_type_decoders()

    assert decoders == [app_decoder, router_decoder, controller_decoder, handler_decoder]
