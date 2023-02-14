from starlite import Starlite
from starlite.middleware.session.memory_backend import MemoryBackendConfig

session_config = MemoryBackendConfig()

app = Starlite(middleware=[session_config.middleware])
