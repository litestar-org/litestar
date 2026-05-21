from litestar import Litestar, Request, get


@get("/", sync_to_thread=False)
def index(request: Request) -> dict[str, str]:
    return {"method": request.method}


app = Litestar(route_handlers=[index])
