from re import A

from pydantic import BaseModel, Field
from pydantic_openapi_schema.v3_1_0 import Components, Example, Header

from starlite import OpenAPIConfig, Starlite, get
from starlite.handlers.http import post
from starlite.testing.client.sync_client import TestClient


def test_merged_components_correct() -> None:
    components_one = Components(headers={"one": Header()})
    components_two = Components(headers={"two": Header()})
    components_three = Components(examples={"example-one": Example(summary="an example")})
    config = OpenAPIConfig(
        title="my title", version="1.0.0", components=[components_one, components_two, components_three]
    )
    openapi = config.to_openapi_schema()
    assert openapi.components.dict(exclude_none=True) == {  # type: ignore[union-attr]
        "examples": {"example-one": {"summary": "an example"}},
        "headers": {
            "one": {
                "name": "",
                "param_in": "header",
                "required": False,
                "deprecated": False,
                "allowEmptyValue": False,
                "allowReserved": False,
            },
            "two": {
                "name": "",
                "param_in": "header",
                "required": False,
                "deprecated": False,
                "allowEmptyValue": False,
                "allowReserved": False,
            },
        },
    }


def test_by_alias() -> None:
    class ModelWithAlias(BaseModel):
        first: str = Field(alias="second")
        underscore: str = Field(alias="_underscore")

    @get("/")
    def handler() -> ModelWithAlias:
        return ModelWithAlias(second="abc", _underscore="test")

    @post("/")
    def handler_post(data: ModelWithAlias) -> None:
        return

    app = Starlite(
        route_handlers=[handler, handler_post],
        openapi_config=OpenAPIConfig(title="my title", version="1.0.0", by_alias=True),
    )

    assert app.openapi_schema
    assert app.openapi_schema.dict(exclude_none=True)["components"]["schemas"]["ModelWithAlias"] == {
        "properties": {
            "second": {"type": "string", "title": "Second"},
            "_underscore": {"type": "string", "title": " Underscore"},
        },
        "type": "object",
        "required": ["second", "_underscore"],
        "title": "ModelWithAlias",
    }

    with TestClient(app=app) as client:
        assert client.get("/").json() == {"second": "abc", "_underscore": "test"}

        assert client.post("/", json={"second": "abc", "_underscore": "test"}).status_code == 201

    app = Starlite(
        route_handlers=[handler, handler_post],
        openapi_config=OpenAPIConfig(title="my title", version="1.0.0", by_alias=False),
    )

    assert app.openapi_schema
    assert app.openapi_schema.dict(exclude_none=True)["components"]["schemas"]["ModelWithAlias"] == {
        "properties": {
            "first": {"type": "string", "title": "Second"},
            "underscore": {"type": "string", "title": " Underscore"},
        },
        "type": "object",
        "required": ["first", "underscore"],
        "title": "ModelWithAlias",
    }

    with TestClient(app=app) as client:
        assert client.get("/").json() == {"first": "abc", "underscore": "test"}

        assert client.post("/", json={"first": "abc", "underscore": "test"}).status_code == 201
