from litestar import Litestar, get, post
from litestar.dto import DTOFactory
from tests import Person


def test_dto_openapi_generation() -> None:
    DTO = DTOFactory()("UserCreateDTO", Person, field_mapping={"last_name": ("surname", str)}, exclude=["optional"])

    @get(path="/user")
    def get_user() -> DTO:  # type: ignore
        ...

    @post(path="/user")
    def create_user(data: DTO) -> DTO:  # type: ignore
        ...

    app = Litestar(route_handlers=[get_user, create_user])
    assert app.openapi_schema
