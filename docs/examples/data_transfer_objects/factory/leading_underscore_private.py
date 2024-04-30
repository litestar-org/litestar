from dataclasses import dataclass

from litestar import Litestar, post
from litestar.dto import DataclassDTO


@dataclass
class Foo:
    this_will: str
    _this_will: str = "Mars"


@post("/", dto=DataclassDTO[Foo], sync_to_thread=False)
def handler(data: Foo) -> Foo:
    return data


app = Litestar(route_handlers=[handler])

# run: / -H "Content-Type: application/json" -d '{"bar":"stay","_baz":"go_away!"}'
