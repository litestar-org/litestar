from typing import Dict, Optional, Type, cast

from aiomcache import Client as MemcacheClient

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig


class MemcachedBackend(ServerSideBackend["MemcachedBackendConfig"]):
    __slots__ = ("memcached",)

    def __init__(self, config: "MemcachedBackendConfig") -> None:
        """Session backend to store data in memcached.

        Notes:
            - Requires `aiomcache`. Install with `pip install starlite[memcached]`
        """
        super().__init__(config=config)
        self.memcached = config.memcached

    def _id_to_storage_key(self, session_id: str) -> bytes:
        return f"{self.config.key_prefix}:{session_id}".encode()

    async def get(self, session_id: str) -> Optional[bytes]:
        """Retrieve data associated with `session_id` from memcached.

        Args:
            session_id: The session-ID

        Returns:
            The session data, if existing, otherwise `None`.
        """
        data = await self.memcached.get(key=self._id_to_storage_key(session_id))  # type: ignore[call-overload]
        return cast("Optional[bytes]", data)

    async def set(self, session_id: str, data: bytes) -> None:
        """Store `data` in memcached under `<prefix>:<session_id>`. If there is
        already data associated with `session_id`, replace it with `data` and
        reset its expiry time.

        Args:
            session_id: The session-ID
            data: Serialized session data

        Returns:
            None
        """
        await self.memcached.set(key=self._id_to_storage_key(session_id), value=data, exptime=self.config.max_age)

    async def delete(self, session_id: str) -> None:
        """Delete the data associated with `session_id`. Fail silently if no
        such session-ID exists.

        Args:
            session_id: The session-ID

        Returns:
            None
        """
        await self.memcached.delete(self._id_to_storage_key(session_id))

    async def delete_all(self) -> None:
        """Delete all data stored within this backend.

        Returns:
            None

        Notes:
            This has poor performance since memcached does not offer utilities to
            properly scan or match keys by prefix.
        """
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
    _backend_class: Type[MemcachedBackend] = MemcachedBackend
    memcached: MemcacheClient
    """An `aiomcache.Client` instance"""
    key_prefix: str = "STARLITE_SESSION"
    """Prefix to store data under after the schema of `<prefix>:<session-ID>`"""
