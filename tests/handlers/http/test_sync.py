import pytest

from litestar import MediaType, get
from litestar.exceptions import LitestarWarning
from litestar.handlers.http_handlers import HTTPRouteHandler
from litestar.testing import create_test_client


def sync_handler() -> str:
    return "Hello World"


@pytest.mark.parametrize(
    "handler",
    [
        get("/", media_type=MediaType.TEXT, sync_to_thread=True)(sync_handler),
        get("/", media_type=MediaType.TEXT, sync_to_thread=False)(sync_handler),
    ],
)
def test_sync_to_thread(handler: HTTPRouteHandler) -> None:
    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.text == "Hello World"


def test_sync_to_thread_not_set_warns() -> None:
    with pytest.warns(LitestarWarning):
        get("/")(sync_handler)
