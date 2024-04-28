from litestar import get
from litestar.contrib.htmx.response import Retarget


@get("/contact-us")
def handler() -> Retarget:
    return Retarget(content="Success!", target="#new-target")
