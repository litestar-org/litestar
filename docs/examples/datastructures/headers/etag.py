import random
import time

from litestar import Controller, Litestar, get
from litestar.datastructures import ETag
from litestar.enums import MediaType
from litestar.response import Response


class MyController(Controller):
    etag = ETag(value="foo")

    @get("/chance_of_rain")
    def get_chance_of_rain(self) -> float:
        """This endpoint uses the etag value in the controller which overrides the app value.

        The returned header will be `etag: "foo"`
        """
        return 0.5

    @get("/timestamp", etag=ETag(value="bar"))
    def get_server_time(self) -> float:
        """This endpoint overrides the etag defined in the controller.

        The returned header will be `etag: W/"bar"`
        """
        return time.time()


@get("/population")
def get_population_count() -> int:
    """This endpoint will use the etag defined in the app.

    The returned header will be `etag: "bar"`
    """
    return 100000


@get("/population-dynamic", etag=ETag(documentation_only=True))
def get_population_count_dynamic() -> Response[str]:
    """The etag defined in this route handler will not be returned, and does not need a value.

    It will only be used for OpenAPI generation.
    """
    population_count = random.randint(0, 1000)
    return Response(
        content=str(population_count),
        headers={"etag": str(population_count)},
        media_type=MediaType.TEXT,
        status_code=200,
    )


app = Litestar(
    route_handlers=[MyController, get_population_count], etag=ETag(value="bar")
)
