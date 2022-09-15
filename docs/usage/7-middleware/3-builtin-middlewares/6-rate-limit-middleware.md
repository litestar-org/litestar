# Rate-Limit Middleware

Starlite includes an optional `RateLimitMiddleware` that follows
the [IETF RateLimit draft specification](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/).

To use the rate limit middleware, use the `RateLimitConfig`:

```python
from starlite import Starlite
from starlite.middleware import RateLimitConfig

RateLimitConfig(
    rate_limit=("second", 1),
    exclude=["/schema"],
)

app = Starlite(route_handlers=[...], middleware=[RateLimitConfig.middleware])
```

The only required configuration kwarg is `rate_limit`, which expects a tuple containing a time-unit (`second`, `minute`
, `hour`, `day`) and a value for the request quota (integer). For the other configuration options,
[see the additional configuration options in the reference][starlite.middleware.rate_limit.RateLimitConfig].
