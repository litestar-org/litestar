from litestar import Litestar
from litestar.middleware.rate_limit import RateLimitConfig, RateLimitMiddleware

app = Litestar(middleware=[RateLimitMiddleware(RateLimitConfig(("second", 1)))])
rate_limit_store = app.stores.get("rate_limit")
