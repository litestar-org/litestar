from typing import List, cast

import pytest
from starlette.status import HTTP_200_OK, HTTP_201_CREATED
from tortoise import Tortoise, fields
from tortoise.models import Model

from starlite import get, post
from starlite.plugins.tortoise_orm import TortoiseORMPlugin
from starlite.testing import create_test_client


class Tournament(Model):  # type: ignore[misc]
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    optional = fields.TextField(null=True)
    events: fields.ReverseRelation["Event"]

    class Meta:
        ordering = ["name"]


class Event(Model):  # type: ignore[misc]
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    tournament: fields.ForeignKeyNullableRelation[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events", null=True
    )
    participants: fields.ManyToManyRelation["Team"] = fields.ManyToManyField(
        "models.Team", related_name="events", through="event_team"
    )
    address: fields.OneToOneNullableRelation["Address"]

    class Meta:
        ordering = ["name"]


class Address(Model):  # type: ignore[misc]
    city = fields.CharField(max_length=64)
    street = fields.CharField(max_length=128)
    created_at = fields.DatetimeField(auto_now_add=True)

    event: fields.OneToOneRelation[Event] = fields.OneToOneField(
        "models.Event", on_delete=fields.CASCADE, related_name="address", pk=True
    )

    class Meta:
        ordering = ["city"]


class Team(Model):  # type: ignore[misc]
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    events: fields.ManyToManyRelation[Event]

    class Meta:
        ordering = ["name"]


async def init_tortoise() -> None:
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": [__name__]})
    await Tortoise.generate_schemas()

    # seed data
    tournament = await Tournament.create(name="New Tournament")
    tournament2 = await Tournament.create(name="Old Tournament")
    await Event.create(name="Empty")
    event = await Event.create(name="Test", tournament=tournament)
    event2 = await Event.create(name="TestLast", tournament=tournament)
    event3 = await Event.create(name="Test2", tournament=tournament2)
    await Address.create(city="Santa Monica", street="Ocean", event=event)
    await Address.create(city="Somewhere Else", street="Lane", event=event2)
    team1 = await Team.create(name="Onesies")
    team2 = await Team.create(name="T-Shirts")
    team3 = await Team.create(name="Alternates")
    await event.participants.add(team1, team2, team3)
    await event2.participants.add(team1, team2)
    await event3.participants.add(team1, team3)


async def cleanup() -> None:
    await Tortoise._drop_databases()


@get("/tournaments")
async def get_tournaments() -> List[Tournament]:
    tournaments = await Tournament.all()
    return cast(List[Tournament], tournaments)


@get("/tournaments/{tournament_id:int}")
async def get_tournament(tournament_id: int) -> Tournament:
    tournament = await Tournament.filter(id=tournament_id).first()
    return cast(Tournament, tournament)


@post("/tournaments")
async def create_tournament(data: Tournament) -> Tournament:
    assert isinstance(data, Tournament)
    await data.save()
    await data.refresh_from_db()
    return data


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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
