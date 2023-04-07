from pathlib import Path

from litestar import Litestar
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.file import FileStore

app = Litestar(
    middleware=[ServerSideSessionConfig().middleware],
    stores={"sessions": FileStore(path=Path("session_data"))},
)
