from litestar import get
from litestar.params import FromPath, FromQuery


@get("/{some_path:str}")
async def handler(some_path: FromPath[str], some_query: FromQuery[int]) -> None:
    return None
