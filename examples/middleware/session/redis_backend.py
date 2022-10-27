from redis.asyncio import Redis

from starlite import Starlite
from starlite.middleware.session.redis_backend import RedisBackendConfig

session_config = RedisBackendConfig(redis=Redis(host="localhost", port=6379, db=0))

app = Starlite(route_handlers=[], middleware=[session_config.middleware])
