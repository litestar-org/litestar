from starlite import Starlite, get, post
from starlite.contrib.sqlalchemy_1.plugin import SQLAlchemyPlugin
from starlite.dto import DTOFactory
from tests.contrib.sqlalchemy_1.sql_alchemy_plugin import User


def test_dto_openapi_generation() -> None:
    SQLAlchemyDTOFactory = DTOFactory(plugins=[SQLAlchemyPlugin()])

    UserCreateDTO = SQLAlchemyDTOFactory(
        "UserCreateDTO",
        User,
        field_mapping={"hashed_password": ("password", str)},
    )

    UserReadDTO = SQLAlchemyDTOFactory("UserRead", User, exclude=["hashed_password"])

    @get(path="/user")
    def get_user() -> UserReadDTO:  # type: ignore
        ...

    @post(path="/user")
    def create_user(data: UserCreateDTO) -> UserReadDTO:  # type: ignore
        ...

    app = Starlite(route_handlers=[get_user, create_user], plugins=[SQLAlchemyPlugin()])
    assert app.openapi_schema
