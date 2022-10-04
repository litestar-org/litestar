# Rate-Limit Middleware

::: starlite.middleware.rate_limit.RateLimitConfig
    options:
        members:
            - cache_key_builder
            - check_throttle_handler
            - exclude
            - middleware
            - middleware_class
            - rate_limit
            - rate_limit_limit_header_key
            - rate_limit_policy_header_key
            - rate_limit_remaining_header_key
            - rate_limit_reset_header_key
            - set_rate_limit_headers

::: starlite.middleware.rate_limit.RateLimitMiddleware
    options:
        members:
            - __init__
            - cache_key_from_request
            - create_response_headers
            - retrieve_cached_history
            - set_cached_history
            - should_check_request
