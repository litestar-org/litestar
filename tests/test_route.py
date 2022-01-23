import pytest

from starlite import get, post
from starlite.exceptions import MethodNotAllowedException
from starlite.routing import HTTPRoute


@get(path="/")
def my_get_handler() -> None:
    pass


@post(path="/")
def my_post_handler() -> None:
    pass


@pytest.mark.asyncio
async def test_http_route_raises_for_unsupported_method():
    route = HTTPRoute(path="/", route_handlers=[my_get_handler, my_post_handler])

    with pytest.raises(MethodNotAllowedException):
        await route.handle(scope={"method": "DELETE"}, receive=lambda x: x, send=lambda x: x)
