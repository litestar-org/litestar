from pydantic import BaseModel
from starlette.requests import HTTPConnection, Request
from starlette.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from starlite import create_test_client, get
from starlite.exceptions import PermissionDeniedException
from starlite.middleware import AbstractAuthenticationMiddleware, AuthenticationResult


class User(BaseModel):
    name: str
    id: int


class Auth(BaseModel):
    props: str


user = User(name="moishe", id=100)
auth = Auth(props="abc")

state = {}


class AuthMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, request: HTTPConnection) -> AuthenticationResult:
        param = request.headers.get("Authorization")
        if param in state:
            return state.pop(param)
        raise PermissionDeniedException("unauthenticated")


@get(path="/")
def route_handler(request: Request) -> None:
    assert isinstance(request.user, User)
    assert isinstance(request.auth, Auth)
    return None


def test_authentication_middleware():
    client = create_test_client(route_handlers=[route_handler], middleware=[AuthMiddleware])
    token = "abc"
    error_response = client.get("/", headers={"Authorization": token})
    assert error_response.status_code == HTTP_403_FORBIDDEN
    state[token] = AuthenticationResult(user=user, auth=auth)
    success_response = client.get("/", headers={"Authorization": token})
    assert success_response.status_code == HTTP_200_OK
