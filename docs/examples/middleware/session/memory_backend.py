from starlite import Starlite
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.storage.memory_backend import MemoryStorageBackend

session_config = ServerSideSessionConfig(storage=MemoryStorageBackend())

app = Starlite(middleware=[session_config.middleware])
