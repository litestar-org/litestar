from litestar import Litestar, get
from litestar.params import HeaderParameter


@get("/")
async def handler() -> str:
    return "ok"


app = Litestar(
    route_handlers=[handler],
    parameters={
        "api_version": HeaderParameter(
            annotation=str, name="X-API-Version", pattern=r"^\d+\.\d+$", documentation_only=True
        ),
    },
)
