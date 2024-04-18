from litestar import Litestar, get, Request


@get("/")
def index(request: Request) -> None:
    print(request.method)