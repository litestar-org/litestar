from litestar import get
from litestar.params import FromQuery


@get(sync_to_thread=False)
def handler(q: FromQuery[int]) -> str:
    raise ValueError
