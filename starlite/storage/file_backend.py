from __future__ import annotations

import pickle
import shutil
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from anyio import Lock, Path
from anyio.to_thread import run_sync

from .base import StorageBackend, StorageObject

if TYPE_CHECKING:
    from os import PathLike


class FileStorageBackend(StorageBackend):
    """Session backend to store data in files."""

    __slots__ = ("path", "_lock")

    def __init__(self, path: PathLike) -> None:
        self._lock = Lock()
        self.path = Path(path)

    @staticmethod
    async def _load_from_path(path: Path) -> StorageObject:
        data = await path.read_bytes()
        stored_obj: StorageObject = pickle.loads(data)  # nosec # noqa: SCS113
        return stored_obj

    async def get(self, key: str) -> bytes | None:
        path = self.path / key
        async with self._lock:
            if not await path.exists():
                return None

            wrapped_data = await self._load_from_path(path)
            if not wrapped_data.expired:
                return wrapped_data.data
            await path.unlink()

        return None

    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        await self.path.mkdir(exist_ok=True)
        path = self.path / key
        wrapped_data = StorageObject(
            expires=(datetime.now() + timedelta(seconds=expires)) if expires else None,
            data=value,
        )
        async with self._lock:
            await path.write_bytes(pickle.dumps(wrapped_data))

    async def delete(self, key: str) -> None:
        path = self.path / key
        async with self._lock:
            await path.unlink(missing_ok=True)

    async def delete_all(self) -> None:
        async with self._lock:
            await run_sync(shutil.rmtree, self.path)
            await self.path.mkdir()

    async def delete_expired(self) -> None:
        async for file in self.path.iterdir():
            wrapper = await self._load_from_path(file)
            if wrapper.expired:
                await file.unlink()
