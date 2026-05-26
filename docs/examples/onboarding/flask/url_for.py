from litestar import Litestar, Request, get
from litestar.response import Redirect


@get("/", name="index", sync_to_thread=False)
def index() -> str:
    return "hello"


@get("/hello", sync_to_thread=False)
def hello(request: Request) -> Redirect:
    return Redirect(path=request.url_for("index"))


app = Litestar(route_handlers=[index, hello])
