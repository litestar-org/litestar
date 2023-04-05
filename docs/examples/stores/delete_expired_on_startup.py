from pathlib import Path

from starlite import Starlite
from starlite.stores.file import FileStore

file_store = FileStore(Path("data"))


async def on_startup() -> None:
    await file_store.delete_expired()


app = Starlite(on_startup=[on_startup])
