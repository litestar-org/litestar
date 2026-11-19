from typing import Any

import pytest

from litestar import Litestar, get
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi import OpenAPIConfig
from litestar.openapi.datastructures import ResponseSpec
from litestar.openapi.spec import (
    XML,
    Components,
    Discriminator,
    Example,
    OAuthFlow,
    OAuthFlows,
    OpenAPIMediaType,
    OpenAPIResponse,
    Operation,
    PathItem,
    Schema,
    SecurityScheme,
    Server,
    Tag,
)
from litestar.openapi.spec.encoding import Encoding
from litestar.openapi.spec.enums import OpenAPIType
from litestar.response import ServerSentEvent
from tests.unit.test_openapi.utils import build_document


@get("/events")
async def events() -> ServerSentEvent:
    raise NotImplementedError


def test_server_sent_event_response_openapi_3_1() -> None:
    assert build_document(events)["paths"]["/events"]["get"]["responses"]["200"]["content"] == {
        "text/event-stream": {"schema": {"type": "string"}}
    }


def test_openapi_3_2_document_fields() -> None:
    app = Litestar(
        route_handlers=[events],
        openapi_config=OpenAPIConfig(
            title="test",
            version="1",
            openapi_version="3.2.0",
            self_uri="https://example.com/openapi.json",
            servers=[Server(url="https://example.com", name="production")],
            tags=[
                Tag(name="public", summary="Public API", kind="audience"),
                Tag(name="events", summary="Events", parent="public", kind="nav"),
            ],
            components=Components(
                security_schemes={
                    "oauth": SecurityScheme(
                        type="oauth2",
                        oauth2_metadata_url="https://example.com/.well-known/oauth-authorization-server",
                        deprecated=True,
                        flows=OAuthFlows(
                            device_authorization=OAuthFlow(
                                device_authorization_url="https://example.com/device",
                                token_url="https://example.com/token",
                                scopes={},
                            )
                        ),
                    )
                },
                media_types={
                    "Lines": OpenAPIMediaType(item_schema=Schema(type=OpenAPIType.OBJECT)),
                },
            ),
        ),
    )
    document = app.openapi_schema.to_schema()

    assert document["openapi"] == "3.2.0"
    assert document["paths"]["/events"]["get"]["responses"]["200"]["content"] == {
        "text/event-stream": {
            "itemSchema": {
                "type": "object",
                "properties": {
                    "data": {"type": "string"},
                    "event": {"type": "string"},
                    "id": {"type": "string"},
                    "retry": {"type": "integer", "minimum": 0},
                },
            }
        }
    }
    assert document["$self"] == "https://example.com/openapi.json"
    assert document["servers"] == [{"url": "https://example.com", "name": "production"}]
    assert document["tags"] == [
        {"name": "public", "summary": "Public API", "kind": "audience"},
        {"name": "events", "summary": "Events", "parent": "public", "kind": "nav"},
    ]
    assert document["components"]["securitySchemes"]["oauth"] == {
        "type": "oauth2",
        "oauth2MetadataUrl": "https://example.com/.well-known/oauth-authorization-server",
        "deprecated": True,
        "flows": {
            "deviceAuthorization": {
                "deviceAuthorizationUrl": "https://example.com/device",
                "tokenUrl": "https://example.com/token",
                "scopes": {},
            }
        },
    }
    assert document["components"]["mediaTypes"] == {"Lines": {"itemSchema": {"type": "object"}}}


@pytest.mark.parametrize(
    "spec_object, expected",
    [
        (
            Example(data_value={"id": 1}, serialized_value='{"id":1}'),
            {"dataValue": {"id": 1}, "serializedValue": '{"id":1}'},
        ),
        (
            Discriminator(property_name="kind", default_mapping="#/components/schemas/Other"),
            {"propertyName": "kind", "defaultMapping": "#/components/schemas/Other"},
        ),
        (XML(name="id", node_type="attribute"), {"name": "id", "nodeType": "attribute"}),
        (XML(name="id", attribute=True), {"name": "id", "attribute": True, "wrapped": False}),
        (OpenAPIResponse(description="ok", summary="Success"), {"description": "ok", "summary": "Success"}),
        (
            OpenAPIMediaType(
                item_schema=Schema(type=OpenAPIType.STRING),
                prefix_encoding=[Encoding(content_type="application/json")],
                item_encoding=Encoding(content_type="text/plain"),
            ),
            {
                "itemSchema": {"type": "string"},
                "prefixEncoding": [{"contentType": "application/json", "explode": False, "allowReserved": False}],
                "itemEncoding": {"contentType": "text/plain", "explode": False, "allowReserved": False},
            },
        ),
        (
            PathItem(
                query=Operation(operation_id="search"),
                additional_operations={"COPY": Operation(operation_id="copy")},
            ),
            {
                "query": {"operationId": "search", "deprecated": False},
                "additionalOperations": {"COPY": {"operationId": "copy", "deprecated": False}},
            },
        ),
    ],
)
def test_openapi_3_2_fields(spec_object: Any, expected: dict[str, Any]) -> None:
    assert spec_object.to_schema() == expected


@pytest.mark.parametrize("openapi_version", ["3.0.3", "3", "4.0.0", "3.2.0-rc1", "banana"])
def test_unsupported_openapi_version(openapi_version: str) -> None:
    with pytest.raises(ImproperlyConfiguredException, match="Unsupported OpenAPI version"):
        OpenAPIConfig(title="test", version="1", openapi_version=openapi_version)


def test_self_uri_requires_openapi_3_2() -> None:
    with pytest.raises(ImproperlyConfiguredException, match="'self_uri' requires"):
        OpenAPIConfig(title="test", version="1", self_uri="https://example.com/openapi.json")


@get("/", sync_to_thread=False, responses={400: ResponseSpec(dict[str, int], examples=[Example(data_value={"a": 1})])})
def handler_with_3_2_example() -> None:
    return None


@pytest.mark.parametrize(
    "config, route_handlers, fields",
    [
        ({"tags": [Tag(name="root"), Tag(name="child", parent="root", kind="nav")]}, [], "Tag.kind, Tag.parent"),
        ({"servers": [Server(url="/", name="local")]}, [], "Server.name"),
        (
            {
                "components": Components(
                    security_schemes={"key": SecurityScheme(type="http", scheme="bearer", deprecated=True)}
                )
            },
            [],
            "SecurityScheme.deprecated",
        ),
        ({}, [handler_with_3_2_example], "Example.data_value"),
    ],
    ids=["tag", "server", "security-scheme", "response-example"],
)
def test_openapi_3_2_fields_are_rejected_in_openapi_3_1_documents(
    config: dict[str, Any], route_handlers: list[Any], fields: str
) -> None:
    with pytest.raises(ImproperlyConfiguredException, match=f"^500: {fields} require 'openapi_version' to be 3.2.0"):
        build_document(*route_handlers, **config)

    assert build_document(*route_handlers, openapi_version="3.2.0", **config)
