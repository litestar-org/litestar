from typing import Any

from starlite import CacheConfig, get
from starlite.cache import SimpleCacheBackend
from starlite.testing import create_test_client

from . import after_request_handler, slow_handler


def test_async_handling() -> None:
    class AsyncCacheBackend(SimpleCacheBackend):
        async def set(self, key: str, value: Any, expiration: int) -> Any:  # type: ignore
            super().set(key=key, value=value, expiration=expiration)

        async def get(self, key: str) -> Any:
            return super().get(key=key)

    cache_config = CacheConfig(backend=AsyncCacheBackend())

    with create_test_client(
        route_handlers=[get("/cached-async", cache=True)(slow_handler)],
        after_request=after_request_handler,
        cache_config=cache_config,
    ) as client:
        first_response = client.get("/cached-async")
        first_response_identifier = first_response.headers["unique-identifier"]
        assert first_response_identifier
        second_response = client.get("/cached-async")
        assert second_response.headers["unique-identifier"] == first_response_identifier
        assert first_response.json() == second_response.json()
