from starlite import Starlite
from starlite.middleware.session.server_side import ServerSideSessionConfig

session_config = ServerSideSessionConfig()

app = Starlite(middleware=[session_config.middleware])
