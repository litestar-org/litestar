from datetime import datetime, timedelta
from os import PathLike
from typing import Optional, Tuple, Type

import anyio
import orjson

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig

FileStorageMetadataWrapper = Tuple[str, str]


class FileBackend(ServerSideBackend["FileBackendConfig"]):
    def __init__(self, config: "FileBackendConfig") -> None:
        """Session backend to store data in files."""
        super().__init__(config=config)
        self.path = anyio.Path(config.storage_path)

    def _id_to_storage_path(self, session_id: str) -> anyio.Path:
        return self.path / session_id

    @staticmethod
    async def _load_from_path(path: anyio.Path) -> FileStorageMetadataWrapper:
        wrapped_data: FileStorageMetadataWrapper = orjson.loads(await path.read_bytes())
        return wrapped_data

    @staticmethod
    def _is_expired(wrapped_data: FileStorageMetadataWrapper) -> bool:
        return datetime.fromisoformat(wrapped_data[0]) > datetime.utcnow().replace(tzinfo=None)

    async def get(self, session_id: str) -> Optional[bytes]:
        """Load data associated with `session_id` from a file.

        Args:
            session_id: The session-ID

        Returns:
            The session data, if existing, otherwise `None`.
        """

        path = self._id_to_storage_path(session_id)
        if await path.exists():
            wrapped_data = await self._load_from_path(path)
            if self._is_expired(wrapped_data):
                return wrapped_data[1].encode()
            await path.unlink()
        return None

    async def set(self, session_id: str, data: bytes) -> None:
        """Store `data` alongside metadata under the `session_id`, using the ID
        as a filename. If a file already exists for `session_id`, replace it
        with `data` and reset its expiry time.

        Args:
            session_id: The session-ID
            data: Serialized session data

        Returns:
            None
        """
        await self.path.mkdir(exist_ok=True)
        path = self._id_to_storage_path(session_id)
        wrapped_data: FileStorageMetadataWrapper = (
            (datetime.utcnow().replace(tzinfo=None) + timedelta(seconds=self.config.max_age)).isoformat(),
            data.decode(),
        )
        await path.write_bytes(orjson.dumps(wrapped_data))

    async def delete(self, session_id: str) -> None:
        """Delete the file associated with `session_id`.

        Fails silently if no such file exists

        Args:
            session_id: The session-ID

        Returns:
            None
        """
        path = self._id_to_storage_path(session_id)
        await path.unlink(missing_ok=True)

    async def delete_all(self) -> None:
        """Delete all files in the storage path.

        Returns:
            None
        """
        async for file in self.path.iterdir():
            await file.unlink(missing_ok=True)

    async def delete_expired(self) -> None:
        """Delete expired session files.

        Return:
            None
        """
        async for file in self.path.iterdir():
            wrapper = await self._load_from_path(file)
            if self._is_expired(wrapper):
                await file.unlink()


class FileBackendConfig(ServerSideSessionConfig):
    _backend_class: Type[FileBackend] = FileBackend
    storage_path: PathLike
    """Disk path under which to store session files."""
