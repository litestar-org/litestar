Piccolo ORM Plugin
==================

To use the :class:`PiccoloORMPlugin <starlite.plugins.piccolo_orm.PiccoloORMPlugin>`
import it and pass it to the :class:`Starlite constructor <starlite.app.Starlite>`:

.. code-block:: python

   from starlite import Starlite, post, get
   from starlite.plugins.piccolo_orm import PiccoloORMPlugin

   from piccolo.columns.column_types import (
       JSON,
       JSONB,
       ForeignKey,
       Integer,
       Varchar,
   )
   from piccolo.table import Table


   class RecordingStudio(Table):
       facilities = JSON()
       facilities_b = JSONB()


   class Manager(Table):
       name = Varchar(length=50)


   class Band(Table):
       name = Varchar(length=50)
       manager = ForeignKey(Manager)
       popularity = Integer()


   class Venue(Table):
       name = Varchar(length=100)
       capacity = Integer(secret=True)


   class Concert(Table):
       band_1 = ForeignKey(Band)
       band_2 = ForeignKey(Band)
       venue = ForeignKey(Venue)


   @post("/concert")
   async def create_concert(data: Concert) -> Concert:
       await data.save()
       await data.refresh()
       return data


   @get("/studio/{studio_id:int}")
   async def retrieve_studio(studio_id: int) -> RecordingStudio:
       return await RecordingStudio.select().where(RecordingStudio.id == studio_id)


   @get("/venues")
   async def retrieve_venues() -> list[Venue]:
       return await Venue.select()


   app = Starlite(
       route_handlers=[create_concert, retrieve_studio, retrieve_venues],
       plugins=[PiccoloORMPlugin()],
   )

With the plugin in place, you can use any Piccolo tables as a type in route handlers.
