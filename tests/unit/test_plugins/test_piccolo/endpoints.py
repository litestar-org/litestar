from typing import List

from piccolo.testing import ModelBuilder

from litestar import MediaType, get, post
from litestar.plugins.piccolo import PiccoloDTO
from tests.unit.test_plugins.test_piccolo.tables import Concert, RecordingStudio, Venue

studio = ModelBuilder.build_sync(RecordingStudio, persist=False)
venues = [ModelBuilder.build_sync(Venue, persist=False) for _ in range(3)]


@post("/concert", dto=PiccoloDTO[Concert], return_dto=PiccoloDTO[Concert], media_type=MediaType.JSON)
async def create_concert(data: Concert) -> Concert:
    await data.save()
    await data.refresh()
    return data


@get("/studio", return_dto=PiccoloDTO[RecordingStudio], sync_to_thread=False)
def retrieve_studio() -> RecordingStudio:
    return studio


@get("/venues", return_dto=PiccoloDTO[Venue], sync_to_thread=False)
def retrieve_venues() -> List[Venue]:
    return venues


@get("/plugin/studio")
async def retrieve_studio_plugin() -> RecordingStudio:
    return studio


@get("/plugin/venues")
async def retrieve_venues_plugin() -> List[Venue]:
    return venues
