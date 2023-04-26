from typing import List, cast

from piccolo.testing import ModelBuilder

from starlite import get, post
from tests.plugins.piccolo_orm.tables import Concert, RecordingStudio, Venue

studio = ModelBuilder.build_sync(RecordingStudio, persist=False)
venues = cast("List[Venue]", [ModelBuilder.build_sync(Venue, persist=False) for _ in range(3)])


@post("/concert")
async def create_concert(data: Concert) -> Concert:
    await data.save()
    await data.refresh()
    return data


@get("/studio")
def retrieve_studio() -> RecordingStudio:
    return studio


@get("/venues")
def retrieve_venues() -> List[Venue]:
    return venues
