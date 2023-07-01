from typing import Type

import msgspec
import yaml
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from litestar import Controller, post
from litestar.app import DEFAULT_OPENAPI_CONFIG
from litestar.enums import OpenAPIMediaType
from litestar.openapi import OpenAPIConfig, OpenAPIController
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import create_test_client


def test_openapi_yaml(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client([person_controller, pet_controller], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        assert client.app.openapi_schema
        openapi_schema = client.app.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema/openapi.yaml")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_YAML.value
        assert client.app.openapi_schema
        assert yaml.unsafe_load(response.content) == client.app.openapi_schema.to_schema()


def test_openapi_json(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client([person_controller, pet_controller], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        assert client.app.openapi_schema
        openapi_schema = client.app.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema/openapi.json")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_JSON.value
        assert client.app.openapi_schema
        assert response.json() == client.app.openapi_schema.to_schema()


def test_openapi_yaml_not_allowed(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.enabled_endpoints.discard("openapi.yaml")

    with create_test_client([person_controller, pet_controller], openapi_config=openapi_config) as client:
        assert client.app.openapi_schema
        openapi_schema = client.app.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema/openapi.yaml")
        assert response.status_code == HTTP_404_NOT_FOUND


def test_openapi_json_not_allowed(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.enabled_endpoints.discard("openapi.json")

    with create_test_client([person_controller, pet_controller], openapi_config=openapi_config) as client:
        assert client.app.openapi_schema
        openapi_schema = client.app.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema/openapi.json")
        assert response.status_code == HTTP_404_NOT_FOUND


def test_openapi_custom_path() -> None:
    openapi_config = OpenAPIConfig(title="my title", version="1.0.0", path="/custom_schema_path")
    with create_test_client([], openapi_config=openapi_config) as client:
        response = client.get("/schema")
        assert response.status_code == HTTP_404_NOT_FOUND

        response = client.get("/custom_schema_path")
        assert response.status_code == HTTP_200_OK

        response = client.get("/custom_schema_path/openapi.json")
        assert response.status_code == HTTP_200_OK


def test_openapi_normalizes_custom_path() -> None:
    openapi_config = OpenAPIConfig(title="my title", version="1.0.0", path="custom_schema_path")
    with create_test_client([], openapi_config=openapi_config) as client:
        response = client.get("/custom_schema_path/openapi.json")
        assert response.status_code == HTTP_200_OK

        response = client.get("/custom_schema_path/openapi.json")
        assert response.status_code == HTTP_200_OK


def test_openapi_custom_path_avoids_override() -> None:
    class CustomOpenAPIController(OpenAPIController):
        path = "/custom_docs"

    openapi_config = OpenAPIConfig(title="my title", version="1.0.0", openapi_controller=CustomOpenAPIController)
    with create_test_client([], openapi_config=openapi_config) as client:
        response = client.get("/schema")
        assert response.status_code == HTTP_404_NOT_FOUND

        response = client.get("/custom_docs/openapi.json")
        assert response.status_code == HTTP_200_OK

        response = client.get("/custom_docs/openapi.json")
        assert response.status_code == HTTP_200_OK


def test_openapi_custom_path_overrides_custom_controller_path() -> None:
    class CustomOpenAPIController(OpenAPIController):
        path = "/custom_docs"

    openapi_config = OpenAPIConfig(
        title="my title", version="1.0.0", openapi_controller=CustomOpenAPIController, path="/override_docs_path"
    )
    with create_test_client([], openapi_config=openapi_config) as client:
        response = client.get("/custom_docs")
        assert response.status_code == HTTP_404_NOT_FOUND

        response = client.get("/override_docs_path/openapi.json")
        assert response.status_code == HTTP_200_OK

        response = client.get("/override_docs_path/openapi.json")
        assert response.status_code == HTTP_200_OK


def test_msgspec_schema_generation() -> None:
    class Lookup(msgspec.Struct):
        id: Annotated[
            str,
            msgspec.Meta(
                min_length=12,
                max_length=16,
                description="A unique identifier",
                examples=["e4eaaaf2-d142-11e1-b3e4-080027620cdd"],
            ),
        ]

    @post("/example")
    async def example_route() -> Lookup:
        return Lookup(id="1234567812345678")

    with create_test_client(
        route_handlers=[example_route],
        openapi_config=OpenAPIConfig(
            title="Example API",
            version="1.0.0",
        ),
    ) as client:
        response = client.get("/schema/openapi.json")
        assert response.status_code == HTTP_200_OK
        assert response.json()["components"]["schemas"]["Lookup"]["properties"]["id"] == {
            "description": "A unique identifier",
            "examples": [{"value": "e4eaaaf2-d142-11e1-b3e4-080027620cdd"}],
            "maxLength": 16,
            "minLength": 12,
            "type": "string",
        }


def test_pydantic_schema_generation() -> None:
    class Lookup(BaseModel):
        id: Annotated[
            str,
            Field(
                min_length=12,
                max_length=16,
                description="A unique identifier",
                example="e4eaaaf2-d142-11e1-b3e4-080027620cdd",
            ),
        ]

    @post("/example")
    async def example_route() -> Lookup:
        return Lookup(id="1234567812345678")

    with create_test_client(
        route_handlers=[example_route],
        openapi_config=OpenAPIConfig(
            title="Example API",
            version="1.0.0",
        ),
    ) as client:
        response = client.get("/schema/openapi.json")
        assert response.status_code == HTTP_200_OK
        assert response.json()["components"]["schemas"]["Lookup"]["properties"]["id"] == {
            "description": "A unique identifier",
            "examples": [{"value": "e4eaaaf2-d142-11e1-b3e4-080027620cdd"}],
            "maxLength": 16,
            "minLength": 12,
            "type": "string",
        }
