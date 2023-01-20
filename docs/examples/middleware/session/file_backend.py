from pathlib import Path

from starlite import Starlite
from starlite.middleware.session.file_backend import FileBackendConfig

session_config = FileBackendConfig(storage_path=Path("/path/to/session/storage"))

app = Starlite(route_handlers=[], middleware=[session_config.middleware])
