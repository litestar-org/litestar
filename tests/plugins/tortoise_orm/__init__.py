from typing import List, cast

from tortoise import Model, Tortoise, fields  # type: ignore

from starlite.handlers.http_handlers import get, post


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    optional = fields.TextField(null=True)
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

    event: fields.OneToOneRelation[Event] = fields.OneToOneField("models.Event", related_name="address", pk=True)

    class Meta:
        ordering = ["city"]


class Team(Model):
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
    return await Tournament.all()


@get("/tournaments/{tournament_id:int}")
async def get_tournament(tournament_id: int) -> Tournament:
    tournament = await Tournament.filter(id=tournament_id).first()
    return cast("Tournament", tournament)


@post("/tournaments")
async def create_tournament(data: Tournament) -> Tournament:
    await data.save()
    await data.refresh_from_db()
    return data
