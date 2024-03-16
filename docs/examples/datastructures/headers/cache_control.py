import time

from litestar import Controller, Litestar, get
from litestar.datastructures import CacheControlHeader


class MyController(Controller):
    cache_control = CacheControlHeader(max_age=86_400, public=True)

    @get("/chance_of_rain", sync_to_thread=False)
    def get_chance_of_rain(self) -> float:
        """This endpoint uses the cache control value defined in the controller which overrides the app value."""
        return 0.5

    @get(
        "/timestamp",
        cache_control=CacheControlHeader(no_store=True),
        sync_to_thread=False,
    )
    def get_server_time(self) -> float:
        """This endpoint overrides the cache control value defined in the controller."""
        return time.time()


@get("/population", sync_to_thread=False)
def get_population_count() -> int:
    """This endpoint will use the cache control defined in the app."""
    return 100000


app = Litestar(
    route_handlers=[MyController, get_population_count],
    cache_control=CacheControlHeader(max_age=2_628_288, public=True),
)
