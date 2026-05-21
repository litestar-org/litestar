from litestar import Litestar, get
from litestar.response import Redirect


@get("/", sync_to_thread=False)
def index() -> str:
    return "hello"


@get("/hello", sync_to_thread=False)
def hello() -> Redirect:
    return Redirect(path="/")


app = Litestar(route_handlers=[index, hello])
