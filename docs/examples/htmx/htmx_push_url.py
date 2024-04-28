from litestar import get
from litestar.contrib.htmx.response import PushUrl


@get("/about")
def handler() -> PushUrl:
    return PushUrl(content="Success!", push_url="/about")
