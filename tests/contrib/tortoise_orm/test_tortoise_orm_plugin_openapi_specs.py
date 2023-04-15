from typing import Callable

from litestar import Litestar
from litestar.contrib.tortoise_orm import TortoiseORMPlugin
from litestar.openapi.spec import OpenAPIResponse, Reference, RequestBody, Schema
from tests.contrib.tortoise_orm import (
    create_tournament,
    get_tournament,
    get_tournaments,
)


def test_tortoise_orm_plugin_openapi_spec_generation(scaffold_tortoise: Callable) -> None:
    app = Litestar(
        route_handlers=[create_tournament, get_tournament, get_tournaments],
        plugins=[TortoiseORMPlugin()],
    )
    schema = app.openapi_schema

    assert schema
    assert schema.paths
    assert len(schema.paths) == 2

    tournaments_path = schema.paths["/tournaments"]
    assert tournaments_path

    tournaments_by_id_path = schema.paths["/tournaments/{tournament_id}"]
    assert tournaments_by_id_path

    assert tournaments_path.get
    assert tournaments_path.get.responses
    assert isinstance(tournaments_path.get.responses["200"], OpenAPIResponse)
    assert tournaments_path.get.responses["200"].content
    tournament_get_schema = tournaments_path.get.responses["200"].content["application/json"].schema
    assert isinstance(tournament_get_schema, Schema)
    assert isinstance(tournament_get_schema.items, Reference)
    assert tournament_get_schema.items.ref == "#/components/schemas/Tournament"

    assert tournaments_path.post
    assert tournaments_path.post.responses
    response = tournaments_path.post.responses["201"]
    assert isinstance(response, OpenAPIResponse)
    assert response.content
    tournament_post_schema = response.content["application/json"].schema
    assert isinstance(tournament_post_schema, Reference)
    assert tournament_post_schema.ref == "#/components/schemas/Tournament"

    request_body = tournaments_path.post.request_body
    assert isinstance(request_body, RequestBody)
    assert request_body.content
    request_body_schema = request_body.content["application/json"].schema
    assert isinstance(request_body_schema, Reference)
    assert request_body_schema.ref == "#/components/schemas/TournamentRequestBody"

    assert tournaments_by_id_path.get
    assert tournaments_by_id_path.get.responses
    response = tournaments_by_id_path.get.responses["200"]
    assert isinstance(response, OpenAPIResponse)
    assert response.content
    tournament_get_by_id_schema = response.content["application/json"].schema
    assert isinstance(tournament_get_by_id_schema, Reference)
    assert tournament_get_by_id_schema.ref == "#/components/schemas/Tournament"

    assert schema.components
    assert schema.components.schemas
    assert schema.components.schemas["Tournament"].to_schema() == {
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"},
            "optional": {"oneOf": [{"type": "null"}, {"type": "string"}]},
            "events": {
                "items": {"$ref": "#/components/schemas/tests.contrib.tortoise_orm.Event.jjupoe"},
                "type": "array",
            },
        },
        "type": "object",
        "required": ["created_at", "name"],
        "title": "Tournament",
    }
    assert schema.components
    assert schema.components.schemas
    assert schema.components.schemas["TournamentRequestBody"].to_schema() == {
        "properties": {"name": {"type": "string"}, "optional": {"oneOf": [{"type": "null"}, {"type": "string"}]}},
        "type": "object",
        "required": ["name"],
        "title": "TournamentRequestBody",
    }
