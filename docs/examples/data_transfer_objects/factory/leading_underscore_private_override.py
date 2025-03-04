from dataclasses import dataclass

from litestar import Litestar, post
from litestar.dto import DataclassDTO, DTOConfig


@dataclass
class Foo:
    this_will: str
    _this_will: str = "not_go_away!"


class DTO(DataclassDTO[Foo]):
    config = DTOConfig(underscore_fields_private=False)


@post("/", dto=DTO, sync_to_thread=False)
def handler(data: Foo) -> Foo:
    return data


app = Litestar(route_handlers=[handler])

# run: / -H "Content-Type: application/json" -d '{"this_will":"stay","_this_will":"not_go_away!"}'
