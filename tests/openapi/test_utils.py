from starlite import MediaType, Starlite
from starlite.openapi.utils import get_media_type
from tests.openapi.utils import PersonController


def test_get_media_type():
    for route in Starlite(route_handlers=[PersonController]).router.routes:
        for route_handler in route.route_handler_map.values():
            media_type = get_media_type(route_handler=route_handler)
            if route_handler.media_type:
                assert media_type == route_handler.media_type
            elif route_handler.response_class:
                assert media_type == route_handler.response_class.media_type
            else:
                assert media_type == MediaType.JSON
