from pathlib import Path

from starlite import Starlite
from starlite.middleware.session.file_backend import FileBackend, FileBackendConfig

session_config = FileBackendConfig(storage_path=Path("/path/to/session/storage"))
session_backend = FileBackend(config=session_config)


async def clear_expired_sessions() -> None:
    """Delete all expired sessions."""
    await session_backend.delete_expired()


app = Starlite(middleware=[session_backend.config.middleware])
