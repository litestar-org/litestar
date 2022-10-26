import time
from typing import Dict, Optional, Union

from aiomcache import Client


class FakeAsyncMemcached(Client):
    def __init__(self) -> None:
        self._cache: Dict[str, bytes] = {}
        self._expirations: Dict[str, int] = {}
        self._added_times: Dict[str, float] = {}

    async def get(self, key: Union[bytes, str]) -> Optional[bytes]:  # type: ignore[override]
        normalised_key = key.decode() if isinstance(key, bytes) else key
        if normalised_key in self._cache:
            expiry = self.ttl(key)
            if not expiry or (self._added_times[normalised_key] + expiry > time.monotonic()):
                return self._cache[normalised_key]
        return None

    async def set(self, key: Union[bytes, str], value: bytes, exptime: Optional[int] = 0) -> None:  # type: ignore[override]
        normalised_key = key.decode() if isinstance(key, bytes) else key
        self._cache[normalised_key] = value
        if exptime:
            self._expirations[normalised_key] = exptime
        self._added_times[normalised_key] = time.monotonic()

    async def delete(self, key: Union[bytes, str]) -> None:  # type: ignore[override]
        normalised_key = key.decode() if isinstance(key, bytes) else key
        if normalised_key in self._cache:
            self._cache.pop(normalised_key)

    def ttl(self, key: Union[bytes, str]) -> Optional[int]:
        return self._expirations.get(key.decode() if isinstance(key, bytes) else key)
