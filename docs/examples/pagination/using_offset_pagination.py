import dataclasses
from itertools import islice
from typing import List

from polyfactory.factories.dataclass_factory import DataclassFactory

from litestar import Litestar, get
from litestar.pagination import AbstractSyncOffsetPaginator, OffsetPagination
from litestar.params import FromQuery


@dataclasses.dataclass
class Person:
    id: str
    name: str


class PersonFactory(DataclassFactory[Person]):
    __model__ = Person


# we will implement a paginator - the paginator must implement two methods 'get_total' and 'get_items'
# we would usually use a database for this, but for our case we will "fake" the dataset using a factory.


class PersonOffsetPaginator(AbstractSyncOffsetPaginator[Person]):
    def __init__(self) -> None:
        self.data = PersonFactory.batch(50)

    def get_total(self) -> int:
        return len(self.data)

    def get_items(self, limit: int, offset: int) -> List[Person]:
        return list(islice(islice(self.data, offset, None), limit))


paginator = PersonOffsetPaginator()


# we now create a regular handler. The handler will receive two query parameters - 'limit' and 'offset', which
# we will pass to the paginator.
@get("/people", sync_to_thread=False)
def people_handler(limit: FromQuery[int], offset: FromQuery[int]) -> OffsetPagination[Person]:
    return paginator(limit=limit, offset=offset)


app = Litestar(route_handlers=[people_handler])
