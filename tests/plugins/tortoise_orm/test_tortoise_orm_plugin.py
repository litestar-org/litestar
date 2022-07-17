import pytest
from tortoise import Tortoise, fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model

# Models are taken from the tortoise-orm docs: https://tortoise.github.io/examples/pydantic.html#main-py


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    events: fields.ReverseRelation["Event"]

    class Meta:
        ordering = ["name"]


class Event(Model):
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


class Address(Model):
    city = fields.CharField(max_length=64)
    street = fields.CharField(max_length=128)
    created_at = fields.DatetimeField(auto_now_add=True)

    event: fields.OneToOneRelation[Event] = fields.OneToOneField(
        "models.Event", on_delete=fields.CASCADE, related_name="address", pk=True
    )

    class Meta:
        ordering = ["city"]


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    events: fields.ManyToManyRelation[Event]

    class Meta:
        ordering = ["name"]


@pytest.mark.asyncio
async def test_plugin_integration() -> None:
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": [__name__]})
    await Tortoise.generate_schemas()

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

    pydantic_model = pydantic_model_creator(Tournament)
    result = await pydantic_model.from_tortoise_orm(tournament)
    assert result
