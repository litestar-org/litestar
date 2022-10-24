import shutil
from datetime import datetime, timedelta
from os import PathLike
from typing import ClassVar, Optional, Tuple, Type

import anyio
import orjson

from starlite.middleware.session.base import ServerSideBackend, ServerSideSessionConfig

FileStorageMetadataWrapper = Tuple[str, str]


class FileBackend(ServerSideBackend["FileBackendConfig"]):
    def __init__(self, config: "FileBackendConfig") -> None:
        super().__init__(config=config)
        self.path = anyio.Path(config.storage_path)

    def _id_to_storage_path(self, session_id: str) -> anyio.Path:
        return self.path / session_id

    async def get(self, session_id: str) -> Optional[bytes]:
        path = self._id_to_storage_path(session_id)
        if await path.exists():
            wrapped_data: FileStorageMetadataWrapper = orjson.loads(await path.read_bytes())
            expires, data = wrapped_data
            if datetime.fromisoformat(expires) > datetime.utcnow().replace(tzinfo=None):
                return data.encode()
            await path.unlink()
        return None

    async def set(self, session_id: str, data: bytes) -> None:
        path = self._id_to_storage_path(session_id)
        wrapped_data: FileStorageMetadataWrapper = (
            (datetime.utcnow().replace(tzinfo=None) + timedelta(seconds=self.config.max_age)).isoformat(),
            data.decode(),
        )
        await path.write_bytes(orjson.dumps(wrapped_data))

    async def delete(self, session_id: str) -> None:
        path = self._id_to_storage_path(session_id)
        await path.unlink(missing_ok=True)

    async def delete_all(self) -> None:
        await anyio.to_thread.run_sync(shutil.rmtree, self.path, True)
        await self.path.mkdir()


class FileBackendConfig(ServerSideSessionConfig):
    _backend_class: ClassVar[Type[FileBackend]] = FileBackend
    storage_path: PathLike
