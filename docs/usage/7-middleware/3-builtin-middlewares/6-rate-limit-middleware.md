# Rate-Limit Middleware

Starlite includes an optional [`RateLimitMiddleware`][starlite.middleware.rate_limit.RateLimitMiddleware] that follows
the [IETF RateLimit draft specification](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/).

To use the rate limit middleware, use the [`RateLimitConfig`][starlite.middleware.rate_limit.RateLimitConfig]:

``` py
--8<-- "examples/middleware/rate_limit.py"
```

The only required configuration kwarg is `rate_limit`, which expects a tuple containing a time-unit (`second`, `minute`
, `hour`, `day`) and a value for the request quota (integer). For the other configuration options,
[see the additional configuration options in the reference][starlite.middleware.rate_limit.RateLimitConfig].
