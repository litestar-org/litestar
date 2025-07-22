from litestar import Litestar
from litestar.config.response_cache import ResponseCacheConfig
from litestar.types import HTTPScope


def custom_cache_response_filter(_: HTTPScope, status_code: int) -> bool:
    # Cache only 2xx responses
    return 200 <= status_code < 300


response_cache_config = ResponseCacheConfig(cache_response_filter=custom_cache_response_filter)

# Create the app with a custom cache response filter
app = Litestar(
    response_cache_config=response_cache_config,
)
