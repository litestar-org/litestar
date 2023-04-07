from pathlib import Path

from litestar import Litestar
from litestar.stores.file import FileStore

file_store = FileStore(Path("data"))


async def on_startup() -> None:
    await file_store.delete_expired()


app = Litestar(on_startup=[on_startup])
