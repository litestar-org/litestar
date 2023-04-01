Tortoise ORM Plugin
===================

To use the :class:`TortoiseORMPlugin <.contrib.tortoise_orm.TortoiseORMPlugin>`
import it and pass it to the :class:`Litestar <litestar.app.Litestar>` class:

An example of a Litestar app using the Tortoise ORM plugin with computed fields and relations:

.. code-block:: python

   from typing import cast

   from tortoise import Model, Tortoise, fields
   from tortoise.connection import connections

   from litestar import Litestar, get, post
   from litestar.plugins.tortoise_orm import TortoiseORMPlugin


   class Tournament(Model):
       id = fields.IntField(pk=True)
       name = fields.TextField()
       created_at = fields.DatetimeField(auto_now_add=True)
       optional = fields.TextField(null=True)
       # Add the reverse relations so that they can be used for type hinting.
       events: fields.ReverseRelation["Event"]

       def is_medieval(self) -> bool:
           """Check if the tournament is medieval, to be used as a computed field."""
           return "medieval" in self.name

       class Meta:
           ordering = ["name"]

       class PydanticMeta:
           computed = ["is_medieval"]


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
           "models.Event", related_name="address", pk=True
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


   async def init_tortoise() -> None:
       await Tortoise.init(db_url="sqlite://:memory:", modules={"models": [__name__]})
       await Tortoise.generate_schemas()


   async def shutdown_tortoise() -> None:
       await connections.close_all()


   @get("/tournaments")
   async def get_tournaments() -> list[Tournament]:
       tournaments = await Tournament.all()
       return cast("list[Tournament]", tournaments)


   @get("/tournaments/{tournament_id:int}")
   async def get_tournament(tournament_id: int) -> Tournament:
       tournament = await Tournament.filter(id=tournament_id).first()
       return cast("Tournament", tournament)


   @post("/tournaments")
   async def create_tournament(data: Tournament) -> Tournament:
       assert isinstance(data, Tournament)
       await data.save()
       return data


   @post("/tournaments/{tournament_id:int}/events")
   async def create_event(tournament_id: int, data: Event) -> Event:
       """By default, foreign keys are not available in the data keyword argument,
       so we need to add it manually."""
       assert isinstance(data, Event)
       tournament = await Tournament.get(id=tournament_id)
       data.tournament = tournament
       await data.save()
       await data.refresh_from_db()
       return data


   @get("/tournaments/{tournament_id:int}/events")
   async def get_events(tournament_id: int) -> list[Event]:
       tournament = await Tournament.get(id=tournament_id)
       events = await tournament.events.all()
       return cast("list[Event]", events)


   @post("/tournaments/{tournament_id:int}/events")
   async def create_event(tournament_id: int, data: Event) -> Event:
       """By default, foreign keys are not available in the data keyword argument,
       so we need to add it manually."""
       assert isinstance(data, Event)
       tournament = await Tournament.get(id=tournament_id)
       data.tournament = tournament
       await data.save()
       await data.refresh_from_db()
       return data


   app = Litestar(
       route_handlers=[
           get_tournament,
           get_tournaments,
           create_tournament,
           get_events,
           create_event,
       ],
       on_startup=[init_tortoise],
       on_shutdown=[shutdown_tortoise],
       plugins=[TortoiseORMPlugin()],
   )

With the plugin in place, you can use any Tortoise model as a type in route handlers.
