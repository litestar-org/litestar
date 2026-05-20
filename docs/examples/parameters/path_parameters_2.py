import dataclasses
from datetime import UTC, datetime

from litestar import Litestar, get
from litestar.params import FromPath


@dataclasses.dataclass
class Order:
    id: int
    customer_id: int


ORDERS_BY_DATETIME = {
    datetime.fromtimestamp(1667924386, tz=UTC): [
        Order(id=1, customer_id=2),
        Order(id=2, customer_id=2),
    ]
}


@get(path="/orders/{from_date:int}", sync_to_thread=False)
def get_orders(from_date: FromPath[datetime]) -> list[Order]:
    return ORDERS_BY_DATETIME[from_date]


app = Litestar(route_handlers=[get_orders])
