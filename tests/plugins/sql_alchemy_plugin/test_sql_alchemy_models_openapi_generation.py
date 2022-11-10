from starlite import Starlite, get, post
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from tests.plugins.sql_alchemy_plugin import User


@get(path="/user")
def get_user() -> User:
    return User()


@post(path="/user")
def create_user(data: User) -> User:
    return data


def test_sql_alchemy_models_openapi_generation() -> None:
    app = Starlite(route_handlers=[get_user, create_user], plugins=[SQLAlchemyPlugin()])
    assert len(app.openapi_schema.paths) == 1  # type: ignore
    assert (
        app.openapi_schema.paths["/user"].get.responses["200"].content["application/json"].media_type_schema.ref  # type: ignore
        == "#/components/schemas/User"
    )
    assert (
        app.openapi_schema.paths["/user"].post.responses["201"].content["application/json"].media_type_schema.ref  # type: ignore
        == "#/components/schemas/User"
    )
    assert (
        app.openapi_schema.paths["/user"].post.requestBody.content["application/json"].media_type_schema.ref  # type: ignore
        == "#/components/schemas/User"
    )
    assert app.openapi_schema.components.schemas["User"].dict(exclude_none=True) == {  # type: ignore
        "properties": {
            "id": {"type": "integer", "title": "Id"},
            "name": {"type": "string", "title": "Name", "default": "moishe"},
            "company_id": {"type": "integer", "title": "Company Id"},
            "pets": {"title": "Pets"},
            "friends": {"items": {"ref": "#/components/schemas/User"}, "type": "array", "title": "Friends"},
            "company": {"ref": "#/components/schemas/Company"},
        },
        "type": "object",
        "required": ["id"],
        "title": "User",
    }
    assert app.openapi_schema.components.schemas["Company"].dict(exclude_none=True) == {  # type: ignore
        "properties": {
            "id": {"type": "integer", "title": "Id"},
            "name": {"type": "string", "title": "Name"},
            "worth": {"type": "number", "title": "Worth"},
        },
        "type": "object",
        "required": ["id"],
        "title": "Company",
    }
