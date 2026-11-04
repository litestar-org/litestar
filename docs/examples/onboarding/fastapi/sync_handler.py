import time

from litestar import Litestar, get


@get("/", sync_to_thread=True)
def slow_handler() -> dict[str, str]:
    time.sleep(0.01)
    return {"hello": "world"}


@get("/fast", sync_to_thread=False)
def fast_handler() -> dict[str, str]:
    return {"hello": "world"}


app = Litestar(route_handlers=[slow_handler, fast_handler])
