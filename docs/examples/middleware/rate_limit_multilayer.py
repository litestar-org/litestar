from litestar import Litestar, get
from litestar.controller import Controller
from litestar.middleware.rate_limit import RateLimitConfig

rate_limit_config = RateLimitConfig(
    rate_limit=("minute", 5),
    store="rate_limit",  # this is the default
)


class MyController(Controller):
    middleware = [RateLimitConfig(rate_limit=("minute", 3), store="rate_limit_controller").middleware]

    @get("/one", sync_to_thread=False)
    def handler(self) -> None:
        return None

    @get(
        "/two",
        sync_to_thread=False,
        middleware=[RateLimitConfig(rate_limit=("minute", 1), store="rate_limit_endpoint").middleware],
    )
    def handler2(self) -> None:
        return None


app = Litestar(route_handlers=[MyController], middleware=[rate_limit_config.middleware])
