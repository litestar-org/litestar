from litestar import get
from litestar.contrib.htmx.response import Reswap


@get("/contact-us")
def handler() -> Reswap:
    return Reswap(content="Success!", method="beforebegin")
