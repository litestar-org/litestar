from pathlib import Path

from starlite import Starlite
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.stores.file import FileStore

store = FileStore(path=Path(".sessions"))
session_config = ServerSideSessionConfig(store=store)


async def clear_expired_sessions() -> None:
    """Delete all expired sessions."""
    await store.delete_expired()


app = Starlite(
    middleware=[session_config.middleware],
    on_startup=[clear_expired_sessions],
    on_shutdown=[clear_expired_sessions],
)
