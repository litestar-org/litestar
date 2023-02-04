Tortoise ORM Plugin
===================

To use the :class:`TortoiseORMPlugin <starlite.plugins.tortoise_orm.TortoiseORMPlugin>`
import it and pass it to the :class:`Starlite constructor <starlite.app.Starlite>`:

.. code-block:: python

   from typing import cast

   from tortoise import Model, Tortoise, fields
   from tortoise.connection import connections

   from starlite import Starlite, get, post
   from starlite.plugins.tortoise_orm import TortoiseORMPlugin


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
       await data.refresh_from_db()
       return data


   app = Starlite(
       route_handlers=[get_tournament, get_tournaments, create_tournament],
       on_startup=[init_tortoise],
       on_shutdown=[shutdown_tortoise],
       plugins=[TortoiseORMPlugin()],
   )

With the plugin in place, you can use any Tortoise model as a type in route handlers.
