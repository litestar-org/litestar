from litestar import Litestar, get
from litestar.datastructures import State
from litestar.di import Provide


class ArqRedis:
    """Stand-in for an ``arq`` Redis client."""


async def get_arq_redis(state: State) -> ArqRedis:
    return state.arq_redis


@get("/", dependencies={"arq_redis": Provide(get_arq_redis)})
async def handler(arq_redis: ArqRedis) -> dict[str, str]:
    return {"type": type(arq_redis).__name__}


app = Litestar(
    route_handlers=[handler],
    state=State({"arq_redis": ArqRedis()}),
)
