from pathlib import Path

from starlite import Starlite
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.stores.file import FileStore

app = Starlite(
    middleware=[ServerSideSessionConfig().middleware],
    stores={"sessions": FileStore(path=Path("session_data"))},
)
