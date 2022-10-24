from typing import Dict, Optional

from aiomcache.client import Client


class FakeAsyncMemcached(Client):
    def __init__(self) -> None:
        self._cache: Dict[bytes, bytes] = {}
        self._expirations: Dict[bytes, int] = {}

    async def get(self, key: bytes) -> Optional[bytes]:  # type: ignore[override]
        return self._cache.get(key)

    async def set(self, key: bytes, value: bytes, exptime: int) -> None:  # type: ignore[override]
        self._cache[key] = value
        self._expirations[key] = exptime

    async def delete(self, key: bytes) -> None:  # type: ignore[override]
        self._cache.pop(key)

    def ttl(self, key: bytes) -> Optional[int]:
        return self._expirations.get(key)
