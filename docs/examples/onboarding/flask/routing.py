from litestar import Litestar, get


@get("/", sync_to_thread=False)
def index() -> str:
    return "Index Page"


@get("/hello", sync_to_thread=False)
def hello() -> str:
    return "Hello, World"


app = Litestar(route_handlers=[index, hello])
