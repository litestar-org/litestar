from datetime import datetime, timedelta
from os import PathLike
from typing import Callable, NamedTuple, Optional, Type

from anyio import Path

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig
from starlite.utils.serialization import decode_json, encode_json


class FileStorageMetadataWrapper(NamedTuple):
    """Metadata of a session file."""

    expires: str
    data: str


class FileBackend(ServerSideBackend["FileBackendConfig"]):
    """Session backend to store data in files."""

    __slots__ = ("path",)

    def __init__(self, config: "FileBackendConfig") -> None:
        """Initialize `FileBackend`

        Args:
            config: A `FileBackendConfig`
        """
        super().__init__(config=config)
        self.path = Path(config.storage_path)

    def _id_to_storage_path(self, session_id: str) -> Path:
        file_name = self.config.make_filename(session_id) if self.config.make_filename else session_id
        return self.path / file_name

    @staticmethod
    async def _load_from_path(path: Path) -> FileStorageMetadataWrapper:
        data = decode_json(await path.read_bytes())
        return FileStorageMetadataWrapper(**data)

    @staticmethod
    def _is_expired(wrapped_data: FileStorageMetadataWrapper) -> bool:
        return datetime.fromisoformat(wrapped_data.expires) > datetime.utcnow().replace(tzinfo=None)

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
                return wrapped_data.data.encode()
            await path.unlink()
        return None

    async def set(self, session_id: str, data: bytes) -> None:
        """Store `data` alongside metadata under the `session_id`, using the ID as a filename. If a file already exists
        for `session_id`, replace it with `data` and reset its expiry time.

        Args:
            session_id: The session-ID
            data: Serialized session data

        Returns:
            None
        """
        await self.path.mkdir(exist_ok=True)
        path = self._id_to_storage_path(session_id)
        wrapped_data = FileStorageMetadataWrapper(
            expires=(datetime.utcnow().replace(tzinfo=None) + timedelta(seconds=self.config.max_age)).isoformat(),
            data=data.decode(),
        )
        await path.write_bytes(encode_json(wrapped_data._asdict()))

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
    """Backend configuration for `FileBackend`"""

    _backend_class: Type[FileBackend] = FileBackend

    storage_path: PathLike
    """Disk path under which to store session files."""
    make_filename: Optional[Callable[[str], str]] = None
    """Callable that turns a session-ID into a filename used for storage.

    By default, the session-ID will be used as a filename
    """
