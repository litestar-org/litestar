from litestar import Litestar, get, post
from litestar.contrib.sqlalchemy_1.plugin import SQLAlchemyPlugin
from tests.contrib.sqlalchemy_1.sql_alchemy_plugin.models import User


@get(path="/user")
def get_user() -> User:
    return User()


@post(path="/user")
def create_user(data: User) -> User:
    return data


def test_sql_alchemy_models_openapi_generation() -> None:
    app = Litestar(route_handlers=[get_user, create_user], plugins=[SQLAlchemyPlugin()])
    assert len(app.openapi_schema.paths) == 1  # type: ignore
    assert (
        app.openapi_schema.paths["/user"].get.responses["200"].content["application/json"].schema.ref  # type: ignore
        == "#/components/schemas/User"
    )
    assert (
        app.openapi_schema.paths["/user"].post.responses["201"].content["application/json"].schema.ref  # type: ignore
        == "#/components/schemas/User"
    )
    assert (
        app.openapi_schema.paths["/user"].post.requestBody.content["application/json"].schema.ref  # type: ignore
        == "#/components/schemas/User"
    )
    assert app.openapi_schema.components.schemas["User"].to_schema() == {  # type: ignore
        "properties": {
            "id": {"type": "integer", "title": "Id"},
            "name": {"type": "string", "title": "Name", "default": "moishe"},
            "company_id": {"type": "integer", "title": "Company Id"},
            "pets": {"title": "Pets"},
            "friends": {"items": {"$ref": "#/components/schemas/User"}, "type": "array", "title": "Friends"},
            "company": {"$ref": "#/components/schemas/Company"},
        },
        "type": "object",
        "required": ["id"],
        "title": "User",
    }
    assert app.openapi_schema.components.schemas["Company"].to_schema() == {  # type: ignore
        "properties": {
            "id": {"type": "integer", "title": "Id"},
            "name": {"type": "string", "title": "Name"},
            "worth": {"type": "number", "title": "Worth"},
        },
        "type": "object",
        "required": ["id"],
        "title": "Company",
    }
