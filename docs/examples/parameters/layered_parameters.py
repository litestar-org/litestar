from typing import Annotated, Union

from litestar import Controller, Litestar, Router, get
from litestar.params import (
    CookieParameter,
    FromHeader,
    FromPath,
    FromQuery,
    HeaderParameter,
    QueryParameter,
)


class MyController(Controller):
    path = "/controller"
    parameters = {
        "controller_param": QueryParameter(annotation=int, lt=100),
    }

    @get("/{path_param:int}", sync_to_thread=False)
    def my_handler(
        self,
        path_param: FromPath[int],
        local_param: FromQuery[str],
        router_param: FromHeader[str],
        controller_param: Annotated[int, QueryParameter(lt=50)],
    ) -> dict[str, Union[str, int]]:
        return {
            "path_param": path_param,
            "local_param": local_param,
            "router_param": router_param,
            "controller_param": controller_param,
        }


router = Router(
    path="/router",
    route_handlers=[MyController],
    parameters={
        "router_param": HeaderParameter(annotation=str, name="MyHeader", pattern="^[a-zA-Z]$", required=False),
    },
)

app = Litestar(
    route_handlers=[router],
    parameters={
        "app_param": CookieParameter(annotation=str, name="special-cookie", required=False),
    },
)
