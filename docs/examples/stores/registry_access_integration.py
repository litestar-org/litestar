from litestar import Litestar
from litestar.middleware.rate_limit import RateLimitMiddleware

app = Litestar(middleware=[RateLimitMiddleware(("second", 1))])
rate_limit_store = app.stores.get("rate_limit")
