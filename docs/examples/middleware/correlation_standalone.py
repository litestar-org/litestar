from litestar import Litestar, Request, get
from litestar.middleware.correlation import CorrelationMiddleware, get_correlation_id


@get("/")
async def index_handler(request: Request) -> dict[str, str | None]:
    return {"correlation_id": get_correlation_id(request.scope)}


app = Litestar(
    route_handlers=[index_handler],
    middleware=[CorrelationMiddleware()],
)
