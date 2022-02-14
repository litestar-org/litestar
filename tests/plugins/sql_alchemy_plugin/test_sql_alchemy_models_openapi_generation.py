from starlite import Starlite, get, post
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from tests.plugins.sql_alchemy_plugin import User


@get(path="/user")
def get_user() -> User:
    ...


@post(path="/user")
def create_user(data: User) -> User:
    ...


def test_sql_alchemy_models_openapi_generation() -> None:
    app = Starlite(route_handlers=[get_user, create_user], plugins=[SQLAlchemyPlugin()])
    assert app.openapi_schema
