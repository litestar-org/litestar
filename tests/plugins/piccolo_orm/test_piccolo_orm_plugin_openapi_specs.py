from starlite import Starlite
from starlite.plugins.piccolo_orm import PiccoloORMPlugin
from tests.plugins.piccolo_orm.endpoints import (
    create_concert,
    retrieve_studio,
    retrieve_venues,
)


def test_piccolo_orm_plugin_openapi_spec_generation() -> None:
    app = Starlite(route_handlers=[retrieve_studio, retrieve_venues, create_concert], plugins=[PiccoloORMPlugin()])
    schema = app.openapi_schema
    assert len(schema.paths) == 3  # type: ignore

    concert_path = schema.paths["/concert"]  # type: ignore
    studio_path = schema.paths["/studio"]  # type: ignore
    venues_path = schema.paths["/venues"]  # type: ignore

    assert (
        concert_path.post.requestBody.content["application/json"].media_type_schema.ref  # type: ignore
        == "#/components/schemas/ConcertRequestBody"
    )
    assert (
        studio_path.get.responses["200"].content["application/json"].media_type_schema.ref  # type: ignore
        == "#/components/schemas/RecordingStudio"
    )
    assert (
        venues_path.get.responses["200"].content["application/json"].media_type_schema.items.ref  # type: ignore
        == "#/components/schemas/Venue"
    )

    assert schema.components.schemas["ConcertRequestBody"].dict(exclude_none=True) == {  # type: ignore
        "properties": {
            "band_1": {"type": "integer", "title": "Band 1"},
            "band_2": {"type": "integer", "title": "Band 2"},
            "venue": {"type": "integer", "title": "Venue"},
        },
        "type": "object",
        "title": "ConcertRequestBody",
    }
    assert schema.components.schemas["RecordingStudio"].dict(exclude_none=True) == {  # type: ignore
        "properties": {
            "id": {"type": "integer", "title": "Id"},
            "facilities": {"type": "string", "schema_format": "json", "title": "Facilities"},
            "facilities_b": {"type": "string", "schema_format": "json", "title": "Facilities B"},
        },
        "type": "object",
        "title": "RecordingStudio",
    }
    assert schema.components.schemas["Venue"].dict(exclude_none=True) == {  # type: ignore
        "properties": {
            "id": {"type": "integer", "title": "Id"},
            "name": {"type": "string", "maxLength": 100, "title": "Name"},
            "capacity": {"type": "integer", "title": "Capacity"},
        },
        "type": "object",
        "title": "Venue",
    }
