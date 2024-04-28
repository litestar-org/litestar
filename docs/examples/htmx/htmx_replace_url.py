from litestar import get
from litestar.contrib.htmx.response import ReplaceUrl


@get("/contact-us")
def handler() -> ReplaceUrl:
    return ReplaceUrl(content="Success!", replace_url="/contact-us")
