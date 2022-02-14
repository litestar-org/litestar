from starlite import Controller, HttpMethod, Router, Starlite, get
from starlite.types import ResponseHeader

router_first = ResponseHeader(value=1)
router_second = ResponseHeader(value=2)
controller_first = ResponseHeader(value=3)
controller_second = ResponseHeader(value=4)
app_first = ResponseHeader(value=5)
app_second = ResponseHeader(value=6)
local_first = ResponseHeader(value=7)
local_second = ResponseHeader(value=8)

test_path = "/test"


class MyController(Controller):
    path = test_path
    response_headers = {"first": controller_first, "second": controller_second}

    @get(
        path="/{path_param:str}",
        response_headers={
            "first": local_first,
        },
    )
    def test_method(self) -> None:
        pass


first_router = Router(
    path="/users", response_headers={"second": router_first, "third": router_second}, route_handlers=[MyController]
)

second_router = Router(path="/external", response_headers={"external": ResponseHeader(value="nope")}, route_handlers=[])

app = Starlite(
    openapi_config=None,
    response_headers={"first": app_first, "fourth": app_second},
    route_handlers=[first_router, second_router],
)


def test_response_headers() -> None:
    route_handler, _ = app.routes[0].route_handler_map[HttpMethod.GET]  # type: ignore
    resolved_headers = route_handler.resolve_response_headers()
    assert resolved_headers["first"].value == local_first.value
    assert resolved_headers["second"].value == controller_second.value
    assert resolved_headers["third"].value == router_second.value
    assert resolved_headers["fourth"].value == app_second.value
    assert "external" not in resolved_headers
