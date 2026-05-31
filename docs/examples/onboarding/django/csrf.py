from litestar import Litestar, post
from litestar.config.csrf import CSRFConfig


@post("/transfer")
async def transfer(data: dict[str, int]) -> dict[str, int]:
    return data


app = Litestar(
    route_handlers=[transfer],
    csrf_config=CSRFConfig(secret="change-me"),
)
