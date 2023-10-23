from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

import msgspec
import pytest
import yaml
from typing_extensions import Annotated

from litestar import Controller, get, post
from litestar.app import DEFAULT_OPENAPI_CONFIG
from litestar.enums import MediaType, OpenAPIMediaType, ParamType
from litestar.openapi import OpenAPIConfig, OpenAPIController
from litestar.serialization.msgspec_hooks import decode_json, encode_json, get_serializer
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import create_test_client

CREATE_EXAMPLES_VALUES = (True, False)


@pytest.mark.parametrize("create_examples", CREATE_EXAMPLES_VALUES)
@pytest.mark.parametrize("schema_path", ["/schema/openapi.yaml", "/schema/openapi.yml"])
def test_openapi(
    person_controller: type[Controller], pet_controller: type[Controller], create_examples: bool, schema_path: str
) -> None:
    openapi_config = OpenAPIConfig("Example API", "1.0.0", create_examples=create_examples)
    with create_test_client([person_controller, pet_controller], openapi_config=openapi_config) as client:
        assert client.app.openapi_schema
        openapi_schema = client.app.openapi_schema
        assert openapi_schema.paths
        response = client.get(schema_path)
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_YAML.value
        assert client.app.openapi_schema
        serializer = get_serializer(client.app.type_encoders)
        schema_json = decode_json(encode_json(openapi_schema.to_schema(), serializer))
        assert response.content.decode("utf-8") == yaml.dump(schema_json)


@pytest.mark.parametrize("create_examples", CREATE_EXAMPLES_VALUES)
def test_openapi_json(
    person_controller: type[Controller], pet_controller: type[Controller], create_examples: bool
) -> None:
    openapi_config = OpenAPIConfig("Example API", "1.0.0", create_examples=create_examples)
    with create_test_client([person_controller, pet_controller], openapi_config=openapi_config) as client:
        assert client.app.openapi_schema
        openapi_schema = client.app.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema/openapi.json")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_JSON.value
        assert client.app.openapi_schema
        serializer = get_serializer(client.app.type_encoders)
        assert response.content == encode_json(openapi_schema.to_schema(), serializer)


@pytest.mark.parametrize(
    "endpoint, schema_path", [("openapi.yaml", "/schema/openapi.yaml"), ("openapi.yml", "/schema/openapi.yml")]
)
def test_openapi_yaml_not_allowed(
    endpoint: str, schema_path: str, person_controller: type[Controller], pet_controller: type[Controller]
) -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.enabled_endpoints.discard(endpoint)

    with create_test_client([person_controller, pet_controller], openapi_config=openapi_config) as client:
        assert client.app.openapi_schema
        openapi_schema = client.app.openapi_schema
        assert openapi_schema.paths
        response = client.get(schema_path)
        assert response.status_code == HTTP_404_NOT_FOUND


def test_openapi_json_not_allowed(person_controller: type[Controller], pet_controller: type[Controller]) -> None:
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


@pytest.mark.parametrize("create_examples", CREATE_EXAMPLES_VALUES)
def test_msgspec_schema_generation(create_examples: bool) -> None:
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
            create_examples=create_examples,
        ),
        signature_types=[Lookup],
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


def test_schema_for_optional_path_parameter() -> None:
    @get(path=["/", "/{test_message:str}"], media_type=MediaType.TEXT, sync_to_thread=False)
    def handler(test_message: Optional[str]) -> str:  # noqa: UP007
        return test_message or "no message"

    with create_test_client(
        route_handlers=[handler],
        openapi_config=OpenAPIConfig(
            title="Example API",
            version="1.0.0",
            create_examples=True,
        ),
    ) as client:
        response = client.get("/schema/openapi.json")
        assert response.status_code == HTTP_200_OK
        assert "parameters" not in response.json()["paths"]["/"]["get"]  # type[ignore]
        parameter = response.json()["paths"]["/{test_message}"]["get"]["parameters"][0]  # type[ignore]
        assert parameter
        assert parameter["in"] == ParamType.PATH
        assert parameter["name"] == "test_message"


T = TypeVar("T")


@dataclass
class Foo(Generic[T]):
    foo: T


def test_with_generic_class() -> None:
    @get("/foo-str", sync_to_thread=False)
    def handler_foo_str() -> Foo[str]:
        return Foo("")

    @get("/foo-int", sync_to_thread=False)
    def handler_foo_int() -> Foo[int]:
        return Foo(1)

    with create_test_client(
        route_handlers=[handler_foo_str, handler_foo_int],
        openapi_config=OpenAPIConfig(
            title="Example API",
            version="1.0.0",
        ),
    ) as client:
        response = client.get("/schema/openapi.json")

        assert response.status_code == HTTP_200_OK
        assert response.json() == {
            "info": {"title": "Example API", "version": "1.0.0"},
            "openapi": "3.1.0",
            "servers": [{"url": "/"}],
            "paths": {
                "/foo-str": {
                    "get": {
                        "summary": "HandlerFooStr",
                        "operationId": "FooStrHandlerFooStr",
                        "responses": {
                            "200": {
                                "description": "Request fulfilled, document follows",
                                "headers": {},
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Foo[str]"}}},
                            }
                        },
                        "deprecated": False,
                    }
                },
                "/foo-int": {
                    "get": {
                        "summary": "HandlerFooInt",
                        "operationId": "FooIntHandlerFooInt",
                        "responses": {
                            "200": {
                                "description": "Request fulfilled, document follows",
                                "headers": {},
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Foo[int]"}}},
                            }
                        },
                        "deprecated": False,
                    }
                },
            },
            "components": {
                "schemas": {
                    "Foo[str]": {
                        "properties": {"foo": {"type": "string"}},
                        "type": "object",
                        "required": ["foo"],
                        "title": "Foo[str]",
                    },
                    "Foo[int]": {
                        "properties": {"foo": {"type": "integer"}},
                        "type": "object",
                        "required": ["foo"],
                        "title": "Foo[int]",
                    },
                }
            },
        }
