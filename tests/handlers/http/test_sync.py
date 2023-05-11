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
    with pytest.warns(LitestarWarning):
        get("/")(sync_handler)
