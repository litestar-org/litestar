from dataclasses import dataclass

from litestar import Litestar, get
from litestar.pagination import AbstractSyncOffsetPaginator, OffsetPagination
from litestar.params import FromQuery


@dataclass
class Item:
    id: int
    name: str


class ItemPaginator(AbstractSyncOffsetPaginator[Item]):
    def __init__(self) -> None:
        self.items = [Item(id=i, name=f"item-{i}") for i in range(100)]

    def get_total(self) -> int:
        return len(self.items)

    def get_items(self, limit: int, offset: int) -> list[Item]:
        return self.items[offset : offset + limit]


paginator = ItemPaginator()


@get("/items", sync_to_thread=False)
def list_items(limit: FromQuery[int], offset: FromQuery[int]) -> OffsetPagination[Item]:
    return paginator(limit=limit, offset=offset)


app = Litestar(route_handlers=[list_items])
