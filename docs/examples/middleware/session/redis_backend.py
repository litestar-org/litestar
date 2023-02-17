from redis.asyncio import Redis

from starlite import Starlite
from starlite.middleware.session.redis_backend import RedisBackendConfig

session_config = RedisBackendConfig(redis=Redis())

app = Starlite(route_handlers=[], middleware=[session_config.middleware])
