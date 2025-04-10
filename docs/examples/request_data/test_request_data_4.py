from dataclasses import dataclass

from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.testing import TestClient


@dataclass
class User:
    id: int
    name: str


@post(path="/")
async def create_user(
    data: Annotated[User, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> User:
    return data


app = Litestar(route_handlers=[create_user])


def test_create_user() -> None:
    with TestClient(app) as client:
        response = client.post("/", data={"id": 1, "name": "johndoe"})
        assert response.status_code == 201
        assert response.json().get("name") == "johndoe"
        assert response.json().get("id") == 1
