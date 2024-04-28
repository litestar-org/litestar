from litestar import get
from litestar.contrib.htmx.response import ClientRefresh


@get("/")
def handler() -> ClientRefresh:
    return ClientRefresh()
