from litestar import get
from litestar.exceptions import HTTPException


@get(sync_to_thread=False)
def handler(q: int) -> str:
    raise HTTPException("nope", status_code=400)
