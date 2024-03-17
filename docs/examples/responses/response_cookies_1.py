from litestar import Controller, Litestar, MediaType, Router, get
from litestar.datastructures import Cookie


class MyController(Controller):
    path = "/controller-path"
    response_cookies = [
        Cookie(
            key="controller-cookie",
            value="controller value",
            description="controller level cookie",
        )
    ]

    @get(
        path="/",
        response_cookies=[
            Cookie(
                key="local-cookie",
                value="local value",
                description="route handler level cookie",
            )
        ],
        media_type=MediaType.TEXT,
        sync_to_thread=False,
    )
    def my_route_handler(self) -> str:
        return "hello world"


router = Router(
    path="/router-path",
    route_handlers=[MyController],
    response_cookies=[
        Cookie(
            key="router-cookie", value="router value", description="router level cookie"
        )
    ],
)

app = Litestar(
    route_handlers=[router],
    response_cookies=[
        Cookie(key="app-cookie", value="app value", description="app level cookie")
    ],
)
