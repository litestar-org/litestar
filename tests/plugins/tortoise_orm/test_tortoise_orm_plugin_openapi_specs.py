from starlite import Starlite
from starlite.plugins.tortoise_orm import TortoiseORMPlugin
from tests.plugins.tortoise_orm import (
    cleanup,
    create_tournament,
    get_tournament,
    get_tournaments,
    init_tortoise,
)


def test_tortoise_orm_plugin_openapi_spec_generation() -> None:
    app = Starlite(
        route_handlers=[create_tournament, get_tournament, get_tournaments],
        on_startup=[init_tortoise],
        on_shutdown=[cleanup],
        plugins=[TortoiseORMPlugin()],
    )
    schema = app.openapi_schema

    assert len(schema.paths) == 2  # type: ignore

    tournaments_path = schema.paths["/tournaments"]  # type: ignore
    tournaments_by_id_path = schema.paths["/tournaments/{tournament_id}"]  # type: ignore
    assert (
        tournaments_path.get.responses["200"].content["application/json"].media_type_schema.items.ref  # type: ignore
        == "#/components/schemas/Tournament"
    )
    assert (
        tournaments_path.post.responses["201"].content["application/json"].media_type_schema.ref  # type: ignore
        == "#/components/schemas/Tournament"
    )
    assert (
        tournaments_path.post.requestBody.content["application/json"].media_type_schema.ref  # type: ignore
        == "#/components/schemas/TournamentRequestBody"
    )
    assert (
        tournaments_by_id_path.get.responses["200"].content["application/json"].media_type_schema.ref  # type: ignore
        == "#/components/schemas/Tournament"
    )

    assert schema.components.schemas["Tournament"].dict(exclude_none=True) == {  # type: ignore
        "properties": {
            "id": {"type": "integer", "maximum": 2147483647.0, "minimum": 1.0, "title": "Id"},
            "name": {"type": "string", "title": "Name"},
            "created_at": {"type": "string", "schema_format": "date-time", "title": "Created At", "readOnly": True},
            "optional": {"type": "string", "title": "Optional"},
        },
        "additionalProperties": False,
        "type": "object",
        "required": ["name", "created_at"],
        "title": "Tournament",
    }
    assert schema.components.schemas["TournamentRequestBody"].dict(exclude_none=True) == {  # type: ignore
        "properties": {
            "name": {"type": "string", "title": "Name"},
            "optional": {"type": "string", "title": "Optional"},
        },
        "additionalProperties": False,
        "type": "object",
        "required": ["name"],
        "title": "TournamentRequestBody",
    }
