from sys import version_info
from typing import Any

import pytest
from pydantic import BaseModel, Field
from pydantic_openapi_schema.v3_1_0 import Components, Example, Header

from starlite import HTTPRouteHandler, Starlite, get
from starlite.config.openapi import OpenAPIConfig


@pytest.mark.skipif(version_info < (3, 10), reason="pydantic serialization differences in lower python versions")
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

    @get("/")
    def handler() -> ModelWithAlias:
        return ModelWithAlias(second="abc")

    app = Starlite(
        route_handlers=[handler], openapi_config=OpenAPIConfig(title="my title", version="1.0.0", by_alias=True)
    )

    assert app.openapi_schema
    assert app.openapi_schema.dict(exclude_none=True)["components"]["schemas"]["ModelWithAlias"] == {
        "properties": {"second": {"type": "string", "title": "Second"}},
        "type": "object",
        "required": ["second"],
        "title": "ModelWithAlias",
    }

    app = Starlite(
        route_handlers=[handler], openapi_config=OpenAPIConfig(title="my title", version="1.0.0", by_alias=False)
    )

    assert app.openapi_schema
    assert app.openapi_schema.dict(exclude_none=True)["components"]["schemas"]["ModelWithAlias"] == {
        "properties": {"first": {"type": "string", "title": "Second"}},
        "type": "object",
        "required": ["first"],
        "title": "ModelWithAlias",
    }


def test_allows_customization_of_operation_id_creator() -> None:
    def operation_id_creator(handler: HTTPRouteHandler, _: Any, __: Any) -> str:
        return handler.name or ""

    @get(path="/1", name="x")
    def handler_1() -> None:
        return

    @get(path="/2", name="y")
    def handler_2() -> None:
        return

    app = Starlite(
        route_handlers=[handler_1, handler_2],
        openapi_config=OpenAPIConfig(title="my title", version="1.0.0", operation_id_creator=operation_id_creator),
    )

    assert app.openapi_schema.dict(exclude_none=True)["paths"] == {  # type: ignore[union-attr]
        "/1": {
            "get": {
                "deprecated": False,
                "operationId": "x",
                "responses": {"200": {"description": "Request fulfilled, document follows", "headers": {}}},
            }
        },
        "/2": {
            "get": {
                "deprecated": False,
                "operationId": "y",
                "responses": {"200": {"description": "Request fulfilled, document follows", "headers": {}}},
            }
        },
    }
