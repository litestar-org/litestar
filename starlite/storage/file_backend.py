from __future__ import annotations

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
        return StorageObject.from_bytes(data)

    async def get(self, key: str, renew: int | None = None) -> bytes | None:
        path = self.path / key
        async with self._lock:
            if not await path.exists():
                return None

            storage_obj = await self._load_from_path(path)
            if not storage_obj.expired:
                if renew and storage_obj.expires:
                    storage_obj.expires = datetime.now() + timedelta(seconds=renew)
                    await path.write_bytes(storage_obj.to_bytes())
                return storage_obj.data
            await path.unlink()

        return None

    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        await self.path.mkdir(exist_ok=True)
        path = self.path / key
        storage_obj = StorageObject(
            expires=(datetime.now() + timedelta(seconds=expires)) if expires else None,
            data=value,
        )
        async with self._lock:
            await path.write_bytes(storage_obj.to_bytes())

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
