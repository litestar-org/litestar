from litestar import Controller, Litestar, MediaType, get
from litestar.datastructures import Cookie


class MyController(Controller):
    path = "/controller-path"
    response_cookies = [Cookie(key="my-cookie", value="123")]

    @get(
        path="/",
        response_cookies=[Cookie(key="my-cookie", value="456")],
        media_type=MediaType.TEXT,
        sync_to_thread=False,
    )
    def my_route_handler(self) -> str:
        return "hello world"


app = Litestar(route_handlers=[MyController])
