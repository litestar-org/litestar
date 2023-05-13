import pytest

from litestar import MediaType, get
from litestar.exceptions import LitestarWarning
from litestar.testing import create_test_client


def sync_handler() -> str:
    return "Hello World"


@pytest.mark.parametrize("sync_to_thread", [True, False])
def test_sync_to_thread(sync_to_thread: bool) -> None:
    handler = get("/", media_type=MediaType.TEXT, sync_to_thread=sync_to_thread)(sync_handler)

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.text == "Hello World"


@pytest.mark.usefixtures("enable_warn_implicit_sync_to_thread")
def test_sync_to_thread_not_set_warns() -> None:
    with pytest.warns(LitestarWarning, match="discouraged since synchronous callables"):
        get("/")(sync_handler)


@pytest.mark.parametrize("sync_to_thread", [True, False])
def test_async_callable_with_sync_to_thread_warns(sync_to_thread: bool) -> None:
    with pytest.warns(LitestarWarning, match="asynchronous callable"):

        @get(sync_to_thread=sync_to_thread)
        async def handler() -> None:
            pass
