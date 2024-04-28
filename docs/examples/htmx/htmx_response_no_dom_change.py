from litestar import get
from litestar.contrib.htmx.response import HXStopPolling


@get("/")
def handler() -> HXStopPolling:
    return HXStopPolling()
