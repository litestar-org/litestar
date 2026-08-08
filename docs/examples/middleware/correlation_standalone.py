from litestar import Litestar, get
from litestar.middleware.correlation import CorrelationContext, CorrelationMiddleware


@get("/")
async def index_handler() -> dict[str, str | None]:
    return {"correlation_id": CorrelationContext.get()}


app = Litestar(
    route_handlers=[index_handler],
    middleware=[CorrelationMiddleware],
)
