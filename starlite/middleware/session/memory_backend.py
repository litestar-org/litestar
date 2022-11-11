from typing import Optional, Type, cast

from starlite.cache.simple_cache_backend import SimpleCacheBackend
from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig


class MemoryBackend(ServerSideBackend["MemoryBackendConfig"]):
    """Session backend to store data in memory."""

    __slots__ = ()
    _cache = SimpleCacheBackend()

    def __init__(self, config: "MemoryBackendConfig") -> None:
        """Initialize `MemoryBackend`.

        Args:
            config: An instance of `MemoryBackendConfig`

        Warning:
            This should not be used in production and serves mainly as a dummy backend
            for easy testing. It is not process-safe, and data won't be persisted
        """
        super().__init__(config=config)

    async def get(self, session_id: str) -> Optional[bytes]:
        """Retrieve data associated with `session_id`.

        Args:
            session_id: The session-ID

        Returns:
            The session data, if existing, otherwise `None`.
        """
        return cast("Optional[bytes]", await self._cache.get(session_id))

    async def set(self, session_id: str, data: bytes) -> None:
        """Store `data` under the `session_id` for later retrieval.

        If there is already data associated with `session_id`, replace
        it with `data` and reset its expiry time

        Args:
            session_id: The session-ID
            data: Serialized session data

        Returns:
            None
        """

        await self._cache.set(session_id, data, expiration=self.config.max_age)

    async def delete(self, session_id: str) -> None:
        """Delete the data associated with `session_id`. Fails silently if no such session-ID exists.

        Args:
            session_id: The session-ID

        Returns:
            None
        """
        await self._cache.delete(session_id)

    async def delete_all(self) -> None:
        """Delete all session data.

        Returns:
            None
        """
        self._cache._store = {}  # pylint: disable=protected-access)


class MemoryBackendConfig(ServerSideSessionConfig):
    """Configuration for `MemoryBackend`"""

    _backend_class: Type[MemoryBackend] = MemoryBackend
