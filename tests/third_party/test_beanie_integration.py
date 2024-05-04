import pytest
from beanie import Document, Indexed, init_beanie
from mongomock_motor import AsyncMongoMockClient  # type: ignore[import]

from starlite import create_test_client, post
from starlite.status_codes import HTTP_201_CREATED


async def initialize_beanie() -> None:
    client = AsyncMongoMockClient()
    await init_beanie(document_models=[Widget], database=client.get_database(name="db"))


class Widget(Document):
    name: Indexed(str, unique=True)  # type: ignore

    class Settings:  # Beanie configuration
        name = "sandbox-widgets"

    class Config:  # Pydantic configuration
        schema_extra = {
            "example": {
                "name": "Widget Name Goes Here",
            },
        }


@post("/widget")
async def create_widget_handler(data: Widget) -> Widget:
    await data.create()
    return data


@pytest.mark.xfail(reason="beanie does not support serialization via '.dict'")
def test_beanie_serialization() -> None:
    with create_test_client(create_widget_handler, on_startup=[initialize_beanie]) as client:
        response = client.post("widget", json={"name": "moishe zuchmir"})
        assert response.status_code == HTTP_201_CREATED
        assert response.json()["name"] == "moishe zuchmir"
