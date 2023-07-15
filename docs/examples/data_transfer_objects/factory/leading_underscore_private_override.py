from dataclasses import dataclass

from litestar import Litestar, post
from litestar.dto import DataclassDTO, DTOConfig


@dataclass
class Foo:
    bar: str
    _baz: str = "Mars"


class DTO(DataclassDTO[Foo]):
    config = DTOConfig(underscore_fields_private=False)


@post("/", dto=DTO, sync_to_thread=False)
def handler(data: Foo) -> Foo:
    return data


app = Litestar(route_handlers=[handler])

# run: / -H "Content-Type: application/json" -d '{"bar":"Hello","_baz":"World!"}'
