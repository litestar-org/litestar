from typing import Any

from litestar import Litestar
from litestar.contrib.piccolo_orm import PiccoloORMPlugin
from litestar.openapi.spec import OpenAPIResponse, Reference, RequestBody, Schema
from tests.contrib.piccolo_orm.endpoints import (
    create_concert,
    retrieve_studio,
    retrieve_venues,
)


def test_piccolo_orm_plugin_openapi_spec_generation() -> None:
    app = Litestar(route_handlers=[retrieve_studio, retrieve_venues, create_concert], plugins=[PiccoloORMPlugin()])
    schema: Any = app.openapi_schema
    assert schema
    assert schema.paths
    assert len(schema.paths) == 3

    concert_path = schema.paths["/concert"]
    studio_path = schema.paths["/studio"]
    venues_path = schema.paths["/venues"]

    assert concert_path.post
    request_body = concert_path.post.request_body
    assert isinstance(request_body, RequestBody)
    assert request_body.content
    schema = request_body.content["application/json"].schema
    assert isinstance(schema, Reference)

    assert schema.ref == "#/components/schemas/ConcertRequestBody"

    assert studio_path.get
    assert studio_path.get.responses
    assert isinstance(studio_path.get.responses["200"], OpenAPIResponse)
    assert studio_path.get.responses["200"].content
    schema = studio_path.get.responses["200"].content["application/json"].schema
    assert isinstance(schema, Reference)
    assert schema.ref == "#/components/schemas/RecordingStudio"

    assert venues_path.get
    assert venues_path.get.responses
    assert isinstance(venues_path.get.responses["200"], OpenAPIResponse)
    assert venues_path.get.responses["200"].content
    schema = venues_path.get.responses["200"].content["application/json"].schema
    assert isinstance(schema, Schema)
    items = schema.items
    assert isinstance(items, Reference)
    assert items.ref == "#/components/schemas/Venue"

    assert app.openapi_schema
    assert app.openapi_schema.components
    assert app.openapi_schema.components.schemas
    assert app.openapi_schema.components.schemas["ConcertRequestBody"].to_schema() == {
        "properties": {
            "band_1": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
            "band_2": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
            "venue": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
        },
        "type": "object",
        "required": [],
        "title": "ConcertRequestBody",
    }
    assert app.openapi_schema.components.schemas["RecordingStudio"].to_schema() == {
        "properties": {
            "id": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
            "facilities": {"oneOf": [{"type": "null"}, {"type": "string"}]},
            "facilities_b": {"oneOf": [{"type": "null"}, {"type": "string"}]},
        },
        "type": "object",
        "required": [],
        "title": "RecordingStudio",
    }
    assert app.openapi_schema.components.schemas["Venue"].to_schema() == {
        "properties": {
            "id": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
            "name": {"oneOf": [{"type": "null"}, {"type": "string", "maxLength": 100}]},
            "capacity": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
        },
        "type": "object",
        "required": [],
        "title": "Venue",
    }
