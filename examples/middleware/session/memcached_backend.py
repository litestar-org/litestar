from aiomcache import Client

from starlite import Starlite
from starlite.middleware.session.memcached_backend import MemcachedBackendConfig

session_config = MemcachedBackendConfig(memcached=Client("127.0.0.1"))

app = Starlite(route_handlers=[], middleware=[session_config.middleware])
