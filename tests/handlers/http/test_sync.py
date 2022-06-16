import pytest

from starlite import HTTPRouteHandler, MediaType, create_test_client, get


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
