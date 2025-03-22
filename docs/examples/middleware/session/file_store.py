from pathlib import Path

from litestar import Litestar
from litestar.middleware.session import SessionMiddleware
from litestar.middleware.session.server_side import ServerSideSessionBackend, ServerSideSessionConfig
from litestar.stores.file import FileStore

app = Litestar(
    middleware=[SessionMiddleware(ServerSideSessionBackend(ServerSideSessionConfig()))],
    stores={"sessions": FileStore(path=Path("session_data"))},
)
