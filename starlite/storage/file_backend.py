from __future__ import annotations

import pickle
import shutil
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, NamedTuple

from anyio import Lock, Path
from anyio.to_thread import run_sync

from .base import StorageBackend

if TYPE_CHECKING:
    from os import PathLike


class FileStorageMetadataWrapper(NamedTuple):
    """Metadata of a session file."""

    expires: datetime | None
    data: bytes


class FileStorageBackend(StorageBackend):
    """Session backend to store data in files."""

    __slots__ = ("path", "_lock")

    def __init__(self, path: PathLike, key_prefix: str | None = None) -> None:
        super().__init__(key_prefix=key_prefix)
        self._lock = Lock()
        self.path = Path(path)

    def with_key_prefix(self, key_prefix: str) -> FileStorageBackend:
        new = type(self)(path=self.path, key_prefix=key_prefix)
        new._lock = self._lock
        return new

    @staticmethod
    def _is_expired(wrapped_data: FileStorageMetadataWrapper) -> bool:
        return wrapped_data.expires is not None and wrapped_data.expires > datetime.now()

    @staticmethod
    async def _load_from_path(path: Path) -> FileStorageMetadataWrapper:
        data = await path.read_bytes()
        wrapped_data: FileStorageMetadataWrapper = pickle.loads(data)  # nosec # noqa: SCS113
        return wrapped_data

    async def get(self, key: str) -> bytes | None:
        path = self.path / self.make_key(key)
        if not await path.exists():
            return None

        async with self._lock:
            wrapped_data = await self._load_from_path(path)
            if self._is_expired(wrapped_data):
                await path.unlink()

        return wrapped_data.data

    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        await self.path.mkdir(exist_ok=True)
        path = self.path / self.make_key(key)
        wrapped_data = FileStorageMetadataWrapper(
            expires=(datetime.now() + timedelta(seconds=expires)) if expires else None,
            data=value,
        )
        async with self._lock:
            await path.write_bytes(pickle.dumps(wrapped_data))

    async def delete(self, key: str) -> None:
        path = self.path / self.make_key(key)
        async with self._lock:
            await path.unlink(missing_ok=True)

    async def delete_all(self) -> None:
        async with self._lock:
            if not self.key_prefix:
                await run_sync(shutil.rmtree, self.path)
                await self.path.mkdir()

            else:
                async for file in self.path.iterdir():
                    if file.name.startswith(self.key_prefix):
                        await file.unlink(missing_ok=True)

    async def delete_expired(self) -> None:
        async for file in self.path.iterdir():
            wrapper = await self._load_from_path(file)
            if self._is_expired(wrapper):
                await file.unlink()
