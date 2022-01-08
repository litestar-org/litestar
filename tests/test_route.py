import pytest
from starlette.routing import NoMatchFound

from starlite import get, post
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
