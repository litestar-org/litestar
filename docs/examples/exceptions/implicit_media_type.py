from litestar import get


@get(sync_to_thread=False)
def handler(q: int) -> str:
    raise ValueError
