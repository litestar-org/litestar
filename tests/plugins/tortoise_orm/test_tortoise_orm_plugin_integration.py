import pytest
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from starlite.plugins.tortoise_orm import TortoiseORMPlugin
from starlite.testing import create_test_client
from tests.plugins.tortoise_orm import (
    Tournament,
    cleanup,
    create_tournament,
    get_tournament,
    get_tournaments,
    init_tortoise,
)


@pytest.mark.asyncio()
async def test_serializing_single_tortoise_model_instance() -> None:
    with create_test_client(
        route_handlers=[get_tournament],
        on_startup=[init_tortoise],
        on_shutdown=[cleanup],
        plugins=[TortoiseORMPlugin()],
    ) as client:
        response = client.get("/tournaments/1")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        db_tournament = (
            await Tournament.filter(id=data["id"])
            .prefetch_related("events__address")
            .prefetch_related("events__participants")
            .first()
        )
        assert db_tournament.name == data["name"]
        assert len(db_tournament.events.related_objects) == len(data["events"])


@pytest.mark.asyncio()
async def test_serializing_list_of_tortoise_models() -> None:
    with create_test_client(
        route_handlers=[get_tournaments],
        on_startup=[init_tortoise],
        on_shutdown=[cleanup],
        plugins=[TortoiseORMPlugin()],
    ) as client:
        response = client.get("/tournaments")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        serialized_tournament = data[0]
        db_tournament = (
            await Tournament.filter(id=serialized_tournament["id"])
            .prefetch_related("events__address")
            .prefetch_related("events__participants")
            .first()
        )
        assert db_tournament.name == serialized_tournament["name"]
        assert len(db_tournament.events.related_objects) == len(serialized_tournament["events"])


@pytest.mark.asyncio()
async def test_creating_a_tortoise_model() -> None:
    with create_test_client(
        route_handlers=[create_tournament],
        on_startup=[init_tortoise],
        on_shutdown=[cleanup],
        plugins=[TortoiseORMPlugin()],
    ) as client:
        response = client.post(
            "/tournaments",
            json={
                "name": "my tournament",
            },
        )
        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert isinstance(data, dict)
        assert data["name"] == "my tournament"
        assert data["id"]
