from litestar import Litestar, Request, get


def set_user_on_request(request: Request) -> None:
    request.state["user"] = request.headers.get("x-user", "anonymous")


@get("/", sync_to_thread=False)
def index(request: Request) -> dict[str, str | None]:
    return {"user": request.state["user"]}


app = Litestar(route_handlers=[index], before_request=set_user_on_request)
