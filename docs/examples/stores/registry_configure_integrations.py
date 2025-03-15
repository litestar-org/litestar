from pathlib import Path

from litestar import Litestar
from litestar.middleware.session import SessionMiddleware
from litestar.middleware.session.server_side import ServerSideSessionBackend, ServerSideSessionConfig
from litestar.stores.file import FileStore
from litestar.stores.redis import RedisStore

app = Litestar(
    stores={
        "sessions": RedisStore.with_client(),
        "response_cache": FileStore(Path("response-cache")),
    },
    middleware=[SessionMiddleware(ServerSideSessionBackend(ServerSideSessionConfig()))],
)
