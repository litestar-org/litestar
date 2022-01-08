import pytest
from starlette.routing import Match, NoMatchFound

from starlite import get, post
from starlite.exceptions import MethodNotAllowedException
from starlite.routing import HTTPRoute


@get(path="/")
def my_get_handler() -> None:
    pass


@post(path="/")
def my_post_handler() -> None:
    pass


def test_url_path_for_multiple_handlers():
    route = HTTPRoute(path="/", route_handlers=[my_get_handler, my_post_handler])

    assert route.url_path_for("my_get_handler")
    assert route.url_path_for("my_post_handler")

    with pytest.raises(NoMatchFound):
        route.url_path_for("unknown_handler")


@pytest.mark.asyncio
async def test_http_route_raises_for_unsupported_method():
    route = HTTPRoute(path="/", route_handlers=[my_get_handler, my_post_handler])

    with pytest.raises(MethodNotAllowedException):
        await route.handle(scope={"method": "DELETE"}, receive=lambda x: x, send=lambda x: x)


def test_match_partial():
    route = HTTPRoute(path="/", route_handlers=[my_get_handler, my_post_handler])
    match, _ = route.matches(scope={"path": "/", "method": "DELETE", "type": "http"})
    assert match == Match.PARTIAL
