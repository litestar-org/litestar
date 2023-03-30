from pathlib import Path

from starlite import Starlite
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.stores.file import FileStore
from starlite.stores.redis import RedisStore

app = Starlite(
    stores={
        "sessions": RedisStore.with_client(),
        "response_cache": FileStore(Path("response-cache")),
    },
    middleware=[ServerSideSessionConfig().middleware],
)
