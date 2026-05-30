from litestar import Litestar, get
from litestar.datastructures import State


class RedisClient:
    """Stand-in for a configured Redis client."""


@get("/")
async def handler(state: State) -> dict[str, str]:
    redis: RedisClient = state.redis
    return {"client": type(redis).__name__}


app = Litestar(
    route_handlers=[handler],
    state=State({"redis": RedisClient()}),
)
