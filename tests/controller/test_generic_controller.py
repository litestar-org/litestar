from __future__ import annotations

from typing import TYPE_CHECKING

from starlite.testing import TestClient

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Any, Callable


def test_generic_controller_scalar(create_module: Callable[[Any], ModuleType]) -> None:
    module = create_module(
        """
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, List, TypeVar

from starlite import Starlite, get, post
from starlite.controller.generic_controller import GenericController
from starlite.di import Provide

T = TypeVar("T")

class AbstractService(Generic[T]):
    def get(self, id: int) -> T:
        ...

    def create(self, data: T) -> T:
        ...

    def get_list(self) -> List[T]:
        ...

class MyGenericController(GenericController[T]):
    @get("/{id:int}")
    def get_handler(self, id: int, service: AbstractService) -> T:
        return service.get(id)

    @post("/")
    def post_handler(self, data: T, service: AbstractService) -> T:
        return service.create(data)

    @get("/")
    def get_collection_handler(self, service: AbstractService) -> List[T]:
        return service.get_list()

@dataclass
class DC:
    a: int
    b: str
    c: List[float]

class Service(AbstractService[DC]):
    def get(self, id: int) -> DC:
        return DC(a=1, b="two", c=[3.0, 4.0])

    def create(self, data: DC) -> DC:
        return DC(a=1, b="two", c=[3.0, 4.0])

    def get_list(self) -> List[T]:
        return [DC(a=1, b="two", c=[3.0, 4.0]) for _ in range(2)]

class ConcreteController(MyGenericController[DC]):
    dependencies = {"service": Provide(lambda: Service())}

app = Starlite(route_handlers=[ConcreteController], openapi_config=None)
"""
    )
    payload = {"a": 1, "b": "two", "c": [3.0, 4.0]}
    with TestClient(app=module.app) as client:
        get_resp = client.get("/1")
        post_resp = client.post("/", json=payload)
        list_resp = client.get("/")
        for resp in get_resp, post_resp:
            assert resp.json() == payload
        assert list_resp.json() == [payload for _ in range(2)]
