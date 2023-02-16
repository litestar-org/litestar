from pathlib import Path

from starlite import Starlite
from starlite.storage.file_backend import FileStorageBackend
from starlite.middleware.session.server_side import ServerSideSessionConfig


storage = FileStorageBackend(path=Path(".sessions"))
session_config = ServerSideSessionConfig(storage=storage)


async def clear_expired_sessions() -> None:
    """Delete all expired sessions."""
    await storage.delete_expired()


app = Starlite(
    middleware=[session_config.middleware],
    on_startup=[clear_expired_sessions],
    on_shutdown=[clear_expired_sessions],
)
