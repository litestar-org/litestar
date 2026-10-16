from litestar import Litestar, post
from litestar.config.csrf import CSRFConfig
from litestar.params import JSONBody


@post("/transfer")
async def transfer(data: JSONBody[dict[str, int]]) -> dict[str, int]:
    return data


app = Litestar(
    route_handlers=[transfer],
    csrf_config=CSRFConfig(secret="change-me"),
)
