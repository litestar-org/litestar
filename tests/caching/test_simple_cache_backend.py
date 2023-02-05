from time import sleep

from starlite import get
from starlite.cache import SimpleCacheBackend
from starlite.config.cache import CacheConfig
from starlite.testing import create_test_client

from . import after_request_handler, slow_handler


async def test_simple_cache_backend(anyio_backend: str) -> None:
    backend = SimpleCacheBackend()
    await backend.set("test", "1", 0.1)  # type: ignore
    value = await backend.get("test")
    assert value
    sleep(0.2)
    value = await backend.get("test")
    assert not value


def test_async_handling() -> None:
    with create_test_client(
        route_handlers=[get("/cached-async", cache=True)(slow_handler)],
        after_request=after_request_handler,
        cache_config=CacheConfig(),
    ) as client:
        first_response = client.get("/cached-async")
        first_response_identifier = first_response.headers["unique-identifier"]
        assert first_response_identifier
        second_response = client.get("/cached-async")
        assert second_response.headers["unique-identifier"] == first_response_identifier
        assert first_response.json() == second_response.json()
