from typing import Callable

from piccolo.testing.model_builder import ModelBuilder

from starlite.plugins.piccolo_orm import PiccoloORMPlugin
from starlite.status_codes import HTTP_200_OK, HTTP_201_CREATED
from starlite.testing import create_test_client
from starlite.utils.serialization import encode_json

from .endpoints import create_concert, retrieve_studio, retrieve_venues, studio, venues
from .tables import Band, Concert, Manager, RecordingStudio, Venue


def test_serializing_single_piccolo_table(scaffold_piccolo: Callable) -> None:
    with create_test_client(route_handlers=[retrieve_studio], plugins=[PiccoloORMPlugin()]) as client:
        response = client.get("/studio")
        assert response.status_code == HTTP_200_OK
        assert str(RecordingStudio(**response.json()).querystring) == str(studio.querystring)


def test_serializing_multiple_piccolo_tables(scaffold_piccolo: Callable) -> None:
    with create_test_client(route_handlers=[retrieve_venues], plugins=[PiccoloORMPlugin()]) as client:
        response = client.get("/venues")
        assert response.status_code == HTTP_200_OK
        assert [str(Venue(**value).querystring) for value in response.json()] == [str(v.querystring) for v in venues]


async def test_create_piccolo_table_instance(scaffold_piccolo: Callable, anyio_backend: str) -> None:
    manager = await ModelBuilder.build(Manager)
    band_1 = await ModelBuilder.build(Band, defaults={Band.manager: manager})
    band_2 = await ModelBuilder.build(Band, defaults={Band.manager: manager})
    venue = await ModelBuilder.build(Venue)
    concert = ModelBuilder.build_sync(
        Concert, persist=False, defaults={Concert.band_1: band_1, Concert.band_2: band_2, Concert.venue: venue}
    )

    with create_test_client(route_handlers=[create_concert], plugins=[PiccoloORMPlugin()]) as client:
        data = concert.to_dict()
        data["band_1"] = band_1.id  # type: ignore[attr-defined]
        data["band_2"] = band_2.id  # type: ignore[attr-defined]
        data["venue"] = venue.id  # type: ignore[attr-defined]
        response = client.post("/concert", content=encode_json(data))
        assert response.status_code == HTTP_201_CREATED
