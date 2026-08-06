from __future__ import annotations

from litestar import get
from litestar.config.response_cache import ResponseCacheConfig
from litestar.middleware.response_cache import ResponseCacheMiddleware
from litestar.params import FromPath
from litestar.testing import create_test_client


def test_defaults_match_config_defaults() -> None:
    middleware = ResponseCacheMiddleware()
    config = ResponseCacheConfig()

    assert middleware.default_expiration == config.default_expiration
    assert middleware.key_builder is config.key_builder
    assert middleware.store == config.store
    assert middleware.cache_response_filter is config.cache_response_filter


def test_middleware_does_not_leak_state_between_sequential_requests() -> None:
    @get("/cached/{value:str}", cache=True)
    def handler(value: FromPath[str]) -> str:
        return value

    with create_test_client([handler]) as client:
        assert client.get("/cached/first").text == "first"
        assert client.get("/cached/second").text == "second"
        assert client.get("/cached/first").text == "first"
        assert client.get("/cached/second").text == "second"
