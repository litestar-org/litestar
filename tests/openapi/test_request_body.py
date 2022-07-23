from starlite import Starlite
from starlite.openapi.request_body import create_request_body
from tests.openapi.utils import PersonController


def test_create_request_body() -> None:
    for route in Starlite(route_handlers=[PersonController]).routes:
        for route_handler, _ in route.route_handler_map.values():  # type: ignore
            handler_fields = route_handler.signature_model.__fields__
            if "data" in handler_fields:
                request_body = create_request_body(field=handler_fields["data"], generate_examples=True, plugins=[])
                assert request_body
