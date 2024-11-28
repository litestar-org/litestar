from litestar import get, Router
from litestar.testing import create_test_client


def test_option_handler_inherits_layer_config() -> None:
    @get("/")
    def handler() -> None:
        return None

    router = Router(path="/router", route_handlers=[handler], response_headers={"router": "router"})

    with create_test_client(route_handlers=[handler, router], response_headers={"app": "app"}) as client:
        res = client.options("/")
        assert res.headers.get("app") == "app"
        assert res.headers.get("router") == "router"
