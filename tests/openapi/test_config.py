from sys import version_info
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import BaseModel, Field

from starlite import Starlite, get
from starlite.exceptions import ImproperlyConfiguredException
from starlite.openapi.config import OpenAPIConfig
from starlite.openapi.spec import Components, Example, OpenAPIHeader, OpenAPIType, Schema

if TYPE_CHECKING:
    from starlite.handlers.http_handlers import HTTPRouteHandler


@pytest.mark.skipif(version_info < (3, 10), reason="pydantic serialization differences in lower python versions")
def test_merged_components_correct() -> None:
    components_one = Components(headers={"one": OpenAPIHeader()}, schemas={"test": Schema(type=OpenAPIType.STRING)})
    components_two = Components(headers={"two": OpenAPIHeader()})
    components_three = Components(examples={"example-one": Example(summary="an example")})
    config = OpenAPIConfig(
        title="my title", version="1.0.0", components=[components_one, components_two, components_three]
    )
    openapi = config.to_openapi_schema()
    assert openapi.components
    assert openapi.components.to_schema() == {
        "schemas": {"test": {"type": "string"}},
        "examples": {"example-one": {"summary": "an example"}},
        "headers": {
            "one": {
                "name": "",
                "in": "header",
                "required": False,
                "deprecated": False,
                "allowEmptyValue": False,
                "allowReserved": False,
            },
            "two": {
                "name": "",
                "in": "header",
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

    app = Starlite(route_handlers=[handler], openapi_config=OpenAPIConfig(title="my title", version="1.0.0"))

    assert app.openapi_schema
    assert app.openapi_schema.to_schema()["components"]["schemas"]["ModelWithAlias"] == {
        "properties": {"second": {"type": "string"}},
        "type": "object",
        "required": ["second"],
        "title": "ModelWithAlias",
    }


def test_allows_customization_of_operation_id_creator() -> None:
    def operation_id_creator(handler: "HTTPRouteHandler", _: Any, __: Any) -> str:
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

    assert app.openapi_schema.to_schema()["paths"] == {
        "/1": {
            "get": {
                "deprecated": False,
                "operationId": "x",
                "responses": {"200": {"description": "Request fulfilled, document follows", "headers": {}}},
                "summary": "Handler1",
            }
        },
        "/2": {
            "get": {
                "deprecated": False,
                "operationId": "y",
                "responses": {"200": {"description": "Request fulfilled, document follows", "headers": {}}},
                "summary": "Handler2",
            }
        },
    }


def test_raises_exception_when_no_config_in_place() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[], openapi_config=None).update_openapi_schema()
