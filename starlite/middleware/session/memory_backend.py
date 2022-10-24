from datetime import datetime, timedelta
from typing import ClassVar, Dict, Optional, Type

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig


class MemoryBackend(ServerSideBackend["MemoryBackendConfig"]):
    def __init__(self, config: "MemoryBackendConfig") -> None:
        super().__init__(config=config)
        self._store: Dict[str, tuple[datetime, bytes]] = {}

    async def get(self, session_id: str) -> Optional[bytes]:
        wrapped_data = self._store.get(session_id)
        if wrapped_data:
            expires, data = wrapped_data
            if expires > datetime.utcnow().replace(tzinfo=None):
                return data
            del self._store[session_id]
        return None

    async def set(self, session_id: str, data: bytes) -> None:
        self._store[session_id] = (
            datetime.utcnow().replace(tzinfo=None) + timedelta(seconds=self.config.max_age),
            data,
        )

    async def delete(self, session_id: str) -> None:
        if session_id in self._store:
            del self._store[session_id]

    async def delete_all(self) -> None:
        self._store = {}


class MemoryBackendConfig(ServerSideSessionConfig):
    _backend_class: ClassVar[Type[MemoryBackend]] = MemoryBackend
