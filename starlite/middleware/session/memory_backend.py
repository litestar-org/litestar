from datetime import datetime, timedelta
from typing import Dict, Optional, Type

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig


class MemoryBackend(ServerSideBackend["MemoryBackendConfig"]):
    def __init__(self, config: "MemoryBackendConfig") -> None:
        """Session backend to store data in memory.

        Notes:
            - This should not be used in production and serves mainly as a dummy backend
            for easy testing. It is not thread or process-safe, and data won't be persisted
        """
        super().__init__(config=config)
        self._store: Dict[str, tuple[datetime, bytes]] = {}

    async def get(self, session_id: str) -> Optional[bytes]:
        """Load data associate with `session_id`"""
        wrapped_data = self._store.get(session_id)
        if wrapped_data:
            expires, data = wrapped_data
            if expires > datetime.utcnow().replace(tzinfo=None):
                return data
            del self._store[session_id]
        return None

    async def set(self, session_id: str, data: bytes) -> None:
        """Store `data` for `session_id`.

        Previously existing data will be overwritten and expiry times
        will be updated
        """
        self._store[session_id] = (
            datetime.utcnow().replace(tzinfo=None) + timedelta(seconds=self.config.max_age),
            data,
        )

    async def delete(self, session_id: str) -> None:
        """Delete data associated with `session_id`.

        Fails silently if no such session-ID exists
        """
        if session_id in self._store:
            del self._store[session_id]

    async def delete_all(self) -> None:
        """Delete all session data stored in redis."""
        self._store = {}


class MemoryBackendConfig(ServerSideSessionConfig):
    _backend_class: Type[MemoryBackend] = MemoryBackend
