from litestar import Litestar, Response, get


@get("/static", status_code=404, sync_to_thread=False)
def static_status() -> str:
    return "not found"


@get("/dynamic", sync_to_thread=False)
def dynamic_status() -> Response[str]:
    return Response("not found", status_code=404)


app = Litestar(route_handlers=[static_status, dynamic_status])
