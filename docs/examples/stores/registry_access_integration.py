from litestar import Litestar
from litestar.middleware.rate_limit import RateLimitConfig

app = Litestar(middleware=[RateLimitConfig(("second", 1)).middleware])
rate_limit_store = app.stores.get("rate_limit")
