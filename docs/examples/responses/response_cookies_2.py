from starlite import Controller, MediaType, Starlite, get
from starlite.datastructures import Cookie


class MyController(Controller):
    path = "/controller-path"
    response_cookies = [Cookie(key="my-cookie", value="123")]

    @get(
        path="/",
        response_cookies=[Cookie(key="my-cookie", value="456")],
        media_type=MediaType.TEXT,
    )
    def my_route_handler(self) -> str:
        return "hello world"


app = Starlite(route_handlers=[MyController])
