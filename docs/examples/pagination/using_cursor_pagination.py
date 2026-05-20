import dataclasses

from polyfactory.factories.dataclass_factory import DataclassFactory

from litestar import Litestar, get
from litestar.pagination import AbstractSyncCursorPaginator, CursorPagination
from litestar.params import FromQuery


@dataclasses.dataclass
class Person:
    id: str
    name: str


class PersonFactory(DataclassFactory[Person]):
    __model__ = Person


# we will implement a paginator - the paginator must implement the method 'get_items'.


class PersonCursorPaginator(AbstractSyncCursorPaginator[str, Person]):
    def __init__(self) -> None:
        self.data = PersonFactory.batch(50)

    def get_items(self, cursor: str | None, results_per_page: int) -> tuple[list[Person], str | None]:
        results = self.data[:results_per_page]
        return results, results[-1].id


paginator = PersonCursorPaginator()


# we now create a regular handler. The handler will receive a single query parameter - 'cursor', which
# we will pass to the paginator.
@get("/people", sync_to_thread=False)
def people_handler(cursor: FromQuery[str | None], results_per_page: FromQuery[int]) -> CursorPagination[str, Person]:
    return paginator(cursor=cursor, results_per_page=results_per_page)


app = Litestar(route_handlers=[people_handler])
