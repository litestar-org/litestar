from typing import Dict
from litestar import get, MediaType


@get(path="/health-check", media_type=MediaType.MESSAGEPACK)
def health_check() -> Dict[str, str]:
    return {"hello": "world"}