from typing import ClassVar, Dict, Optional, Type, cast

from aiomcache import Client as MemcacheClient  # pylint: disable=import-error

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig


class MemcachedBackend(ServerSideBackend["MemcachedBackendConfig"]):
    def __init__(self, config: "MemcachedBackendConfig") -> None:
        super().__init__(config=config)
        self.memcached = config.memcached

    def _id_to_storage_key(self, session_id: str) -> bytes:
        return f"{self.config.key_prefix}:{session_id}".encode()

    async def get(self, session_id: str) -> Optional[bytes]:
        data = await self.memcached.get(key=self._id_to_storage_key(session_id))  # type: ignore[call-overload]
        return cast("Optional[bytes]", data)

    async def set(self, session_id: str, data: bytes) -> None:
        await self.memcached.set(key=self._id_to_storage_key(session_id), value=data, exptime=self.config.max_age)

    async def delete(self, session_id: str) -> None:
        await self.memcached.delete(self._id_to_storage_key(session_id))

    async def delete_all(self) -> None:
        stats: Dict[bytes, Optional[bytes]] = await self.memcached.stats("items")
        for key, raw_val in stats.items():
            if not raw_val:
                continue
            _, slab, field = key.split(b":")
            val = int(raw_val)
            if field != b"number" or val == 0:
                continue
            item_request: Dict[bytes, Optional[bytes]] = await self.memcached.stats(
                "cachedump", slab, str(val + 10).encode()
            )
            for keys in item_request:
                await self.memcached.delete(keys)


class MemcachedBackendConfig(ServerSideSessionConfig):
    _backend_class: ClassVar[Type[MemcachedBackend]] = MemcachedBackend
    memcached: MemcacheClient
    key_prefix: str = "STARLITE_SESSION"
