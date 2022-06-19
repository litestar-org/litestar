from starlite import delete
from starlite.testing import create_test_client


def test_none_response() -> None:
    @delete(path="/")
    async def route() -> None:
        return None

    with create_test_client(route_handlers=[route]) as client:
        response = client.delete("/")
        assert not response.content
