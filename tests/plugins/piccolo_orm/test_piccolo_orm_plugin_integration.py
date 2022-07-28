import uuid
from datetime import date

from orjson import dumps
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from .tables import Concert, RecordingStudio, Band, Manager, Venue
from starlite import get, post
from starlite.plugins.piccolo_orm import PiccoloORMPlugin
from starlite.testing import create_test_client

@post("/concert")
async def create_concert(data: Concert) -> Concert:
    concert = await Concert.objects().create(**data.to_dict())
    return concert

@get("/studio")
def retrieve_studio() -> RecordingStudio:
    return RecordingStudio(records=500, facilities_b={
        "rooms": 10
    })


def test_serializing_single_piccolo_table() -> None:
    with create_test_client(route_handlers=[retrieve_studio], plugins=[PiccoloORMPlugin()]) as client:
        response = client.get("/studio")
        assert response.status_code == HTTP_200_OK


def test_create_piccolo_table_instance(scaffold_piccolo) -> None:
    manager = Manager(touring=True, name="Carlos Batista")
    band_1 = Band(label_id=uuid.uuid4(), date_signed=date.today(), name="The Lemmings", manager=manager, popularity=40)
    band_2 = Band(label_id=uuid.uuid4(), date_signed=date.today(), name="The Cats", manager=manager, popularity=50)
    venue = Venue(name="The Pit", capacity=1000)
    concert = Concert(band_1=band_1, band_2=band_2,venue=venue, net_profit=1000)
    concert.duration = concert.duration.microseconds

    with create_test_client(route_handlers=[create_concert], plugins=[PiccoloORMPlugin()]) as client:
        response = client.post("/concert", data=dumps(concert.to_dict()))
        assert response.status_code == HTTP_201_CREATED