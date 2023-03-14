from starlite import Starlite
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.stores.memory import MemoryStore

session_config = ServerSideSessionConfig(store=MemoryStore())

app = Starlite(middleware=[session_config.middleware])
