from litestar import delete
from litestar.testing import create_test_client


def test_handler_return_none_and_204_status_response_empty() -> None:
    @delete(path="/")
    async def route() -> None:
        return None

    with create_test_client(route_handlers=[route]) as client:
        response = client.delete("/")
        assert not response.content
