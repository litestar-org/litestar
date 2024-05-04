from typing import Any

import pytest
import redis
from pydantic import ValidationError

from starlite import CacheConfig, Starlite
from starlite.cache import CacheBackendProtocol


def test_config_validation_scenario() -> None:
    class ProtocolBaseBackend(CacheBackendProtocol):  # pyright: ignore
        def get(self, key: str) -> None:
            ...

        def set(self, key: str, value: Any, expiration: int) -> None:
            ...

    CacheConfig(backend=ProtocolBaseBackend())

    class NoneProtocolBasedBackend:
        def get(self, key: str) -> None:
            ...

        def set(self, key: str, value: Any, expiration: int) -> None:
            ...

    with pytest.raises(ValidationError):
        CacheConfig(backend=NoneProtocolBasedBackend())  # type: ignore[arg-type]


def test_config_validation_deep_copy() -> None:
    """test fix for issue-333: https://github.com/starlite- api/starlite/issues/333."""

    Starlite(
        route_handlers=[],
        cache_config=CacheConfig(backend=redis.from_url("redis://localhost:6379/1")),  # type: ignore
    )
