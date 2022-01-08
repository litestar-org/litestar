from starlette.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from starlite import BaseRouteHandler, create_test_client, get
from starlite.exceptions import PermissionDeniedException
from starlite.request import Request


async def local_guard(_: Request, route_handler: BaseRouteHandler) -> None:
    if not route_handler.opt or not route_handler.opt.get("allow_all"):
        raise PermissionDeniedException("local")


def app_guard(request: Request, _: BaseRouteHandler) -> None:
    if not request.headers.get("Authorization"):
        raise PermissionDeniedException("app")


@get(path="/secret", guards=[local_guard])
def my_router_handler() -> None:
    ...


client = create_test_client(guards=[app_guard], route_handlers=[my_router_handler])


def test_guards():
    response = client.get("/secret")
    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json().get("detail") == "app"
    response = client.get("/secret", headers={"Authorization": "yes"})
    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json().get("detail") == "local"
    my_router_handler.opt["allow_all"] = True
    response = client.get("/secret", headers={"Authorization": "yes"})
    assert response.status_code == HTTP_200_OK
