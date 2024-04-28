from dataclasses import dataclass
from typing import Generic, List, TypeVar

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.dto import DTOConfig
from litestar.dto.factory.dataclass_factory import DataclassDTO


@dataclass
class User:
    name: str
    age: int


T = TypeVar("T")
V = TypeVar("V")


@dataclass
class Wrapped(Generic[T, V]):
    data: List[T]
    other: V


@get(dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"age"})]])
def handler() -> Wrapped[User, int]:
    return Wrapped(
        data=[User(name="John", age=42), User(name="Jane", age=43)],
        other=2,
    )


app = Litestar(route_handlers=[handler])

# GET "/": {"data": [{"name": "John"}, {"name": "Jane"}], "other": 2}
