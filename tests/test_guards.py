from starlette.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from starlite import create_test_client, get
from starlite.exceptions import PermissionDeniedException
from starlite.request import Request


async def local_guard(request: Request) -> None:
    if not request.headers.get("super-secret"):
        raise PermissionDeniedException("local")


def app_guard(request: Request) -> None:
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
    response = client.get("/secret", headers={"Authorization": "yes", "super-secret": "42"})
    assert response.status_code == HTTP_200_OK
