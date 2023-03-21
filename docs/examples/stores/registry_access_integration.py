from starlite import Starlite
from starlite.middleware.rate_limit import RateLimitConfig

app = Starlite(middleware=[RateLimitConfig(("second", 1)).middleware])
rate_limit_store = app.stores.get("rate_limit")
