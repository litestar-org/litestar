from litestar import get
from litestar.exceptions import HTTPException
from litestar.params import FromQuery


@get(sync_to_thread=False)
def handler(q: FromQuery[int]) -> str:
    raise HTTPException("nope", status_code=400)
