from starlite import Starlite
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.storage.memory import MemoryStorage

session_config = ServerSideSessionConfig(storage=MemoryStorage())

app = Starlite(middleware=[session_config.middleware])
