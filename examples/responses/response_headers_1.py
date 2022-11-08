from starlite import Starlite, Router, Controller, MediaType, get
from starlite.datastructures import ResponseHeader


class MyController(Controller):
    path = "/controller-path"
    response_headers = {
        "controller-level-header": ResponseHeader(value="controller header", description="controller level header")
    }

    @get(
        path="/handler-path",
        response_headers={"my-local-header": ResponseHeader(value="local header", description="local level header")},
        media_type=MediaType.TEXT,
    )
    def my_route_handler(self) -> str:
        return "hello world"


router = Router(
    path="/router-path",
    route_handlers=[MyController],
    response_headers={"router-level-header": ResponseHeader(value="router header", description="router level header")},
)

app = Starlite(
    route_handlers=[router],
    response_headers={"app-level-header": ResponseHeader(value="app header", description="app level header")},
)
