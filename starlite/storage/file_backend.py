from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta
from tempfile import mkstemp
from typing import TYPE_CHECKING

from anyio import Path
from anyio.to_thread import run_sync

from .base import StorageBackend, StorageObject

if TYPE_CHECKING:
    from os import PathLike


class FileStorageBackend(StorageBackend):
    """Session backend to store data in files."""

    __slots__ = ("path", "_lock")

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

    async def get(self, key: str, renew: int | None = None) -> bytes | None:
        path = self.path / key
        storage_obj = await self._load_from_path(path)

        if not storage_obj:
            return None

        if storage_obj.expired:
            await path.unlink(missing_ok=True)
            return None

        if renew and storage_obj.expires:
            storage_obj.expires = datetime.now() + timedelta(seconds=renew)
            await self._write(path, storage_obj)

        return storage_obj.data

    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        await self.path.mkdir(exist_ok=True)
        path = self.path / key
        storage_obj = StorageObject(
            expires=(datetime.now() + timedelta(seconds=expires)) if expires else None,
            data=value,
        )
        await self._write(path, storage_obj)

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
