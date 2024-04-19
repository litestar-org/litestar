from litestar import get, MediaType


@get(path="/health-check", media_type=MediaType.TEXT)
def health_check() -> str:
    return "healthy"