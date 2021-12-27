from starlite import Starlite
from starlite.openapi.request_body import create_request_body
from tests.openapi.utils import PersonController


def test_create_request_body():
    for route in Starlite(route_handlers=[PersonController]).routes:
        for route_handler in route.route_handler_map.values():
            handler_fields = route_handler.__fields__
            if "data" in handler_fields:
                request_body = create_request_body(field=handler_fields["data"], generate_examples=True)
                assert request_body
