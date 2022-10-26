from datetime import datetime, timedelta
from typing import Dict, Optional, Type

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig


class MemoryBackend(ServerSideBackend["MemoryBackendConfig"]):
    def __init__(self, config: "MemoryBackendConfig") -> None:
        """Session backend to store data in memory.

        Warning:
            This should not be used in production and serves mainly as a dummy backend
            for easy testing. It is not thread or process-safe, and data won't be persisted
        """
        super().__init__(config=config)
        self._store: Dict[str, tuple[datetime, bytes]] = {}

    async def get(self, session_id: str) -> Optional[bytes]:
        """Retrieve data associated with `session_id`.

        Args:
            session_id: The session-ID

        Returns:
            The session data, if existing, otherwise `None`.
        """
        wrapped_data = self._store.get(session_id)
        if wrapped_data:
            expires, data = wrapped_data
            if expires > datetime.utcnow().replace(tzinfo=None):
                return data
            del self._store[session_id]
        return None

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
        self._store[session_id] = (
            datetime.utcnow().replace(tzinfo=None) + timedelta(seconds=self.config.max_age),
            data,
        )

    async def delete(self, session_id: str) -> None:
        """Delete the data associated with `session_id`. Fails silently if no
        such session-ID exists.

        Args:
            session_id: The session-ID

        Returns:
            None
        """
        if session_id in self._store:
            del self._store[session_id]

    async def delete_all(self) -> None:
        """Delete all session data.

        Returns:
            None
        """
        self._store = {}


class MemoryBackendConfig(ServerSideSessionConfig):
    _backend_class: Type[MemoryBackend] = MemoryBackend
