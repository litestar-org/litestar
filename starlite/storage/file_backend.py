from __future__ import annotations

import os
import shutil
from tempfile import mkstemp
from typing import TYPE_CHECKING

from anyio import Path
from anyio.to_thread import run_sync

from .base import StorageBackend, StorageObject

if TYPE_CHECKING:
    from datetime import timedelta
    from os import PathLike


class FileStorageBackend(StorageBackend):
    """Session backend to store data in files."""

    __slots__ = ("path",)

    def __init__(self, path: PathLike) -> None:
        self.path = Path(path)

    @staticmethod
    async def _load_from_path(path: Path) -> StorageObject | None:
        try:
            data = await path.read_bytes()
            return StorageObject.from_bytes(data)
        except FileNotFoundError:
            return None

    def _write_sync(self, target_file: Path, storage_obj: StorageObject) -> None:
        try:
            tmp_file_fd, tmp_file_name = mkstemp(dir=self.path, prefix=target_file.name + ".tmp")
            renamed = False
            try:
                try:
                    os.write(tmp_file_fd, storage_obj.to_bytes())
                finally:
                    os.close(tmp_file_fd)

                shutil.move(tmp_file_name, target_file)
                renamed = True
            finally:
                if not renamed:
                    os.unlink(tmp_file_name)  # noqa: PL108
        except OSError:
            pass

    async def _write(self, target_file: Path, storage_obj: StorageObject) -> None:
        await run_sync(self._write_sync, target_file, storage_obj)

    async def set(self, key: str, value: bytes, expires_in: int | timedelta | None = None) -> None:
        await self.path.mkdir(exist_ok=True)
        path = self.path / key
        storage_obj = StorageObject.new(data=value, expires_in=expires_in)
        await self._write(path, storage_obj)

    async def get(self, key: str, renew_for: int | timedelta | None = None) -> bytes | None:
        path = self.path / key
        storage_obj = await self._load_from_path(path)

        if not storage_obj:
            return None

        if storage_obj.expired:
            await path.unlink(missing_ok=True)
            return None

        if renew_for and storage_obj.expires_at:
            await self.set(key, value=storage_obj.data, expires_in=renew_for)

        return storage_obj.data

    async def delete(self, key: str) -> None:
        path = self.path / key
        await path.unlink(missing_ok=True)

    async def delete_all(self) -> None:
        await run_sync(shutil.rmtree, self.path)
        await self.path.mkdir(exist_ok=True)

    async def delete_expired(self) -> None:
        async for file in self.path.iterdir():
            wrapper = await self._load_from_path(file)
            if wrapper and wrapper.expired:
                await file.unlink(missing_ok=True)

    async def exists(self, key: str) -> bool:
        path = self.path / key
        return await path.exists()

    async def expires_in(self, key: str) -> int | None:
        if storage_obj := await self._load_from_path(self.path / key):
            return storage_obj.expires_in
        return None
