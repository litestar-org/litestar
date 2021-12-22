from starlite import Starlite
from starlite.openapi.path_item import create_request_body
from tests.openapi.utils import PersonController


def test_create_request_body():
    for route in Starlite(route_handlers=[PersonController]).router.routes:
        for route_handler in route.route_handler_map.values():
            handler_fields = route_handler.__fields__
            request_body = create_request_body(
                route_handler=route_handler, handler_fields=handler_fields, generate_examples=True
            )
            if "data" in handler_fields:
                assert request_body
            else:
                assert not request_body
