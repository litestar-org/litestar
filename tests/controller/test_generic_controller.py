from __future__ import annotations

from typing import TYPE_CHECKING

from starlite.testing import TestClient

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Any, Callable


def test_generic_controller(create_module: Callable[[Any], ModuleType]) -> None:
    module = create_module(
        """
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from starlite import Starlite, get
from starlite.controller.generic_controller import GenericController
from starlite.di import Provide

if TYPE_CHECKING:
    from typing import Callable

ModelT = TypeVar("ModelT", bound="Base")

@dataclass
class DC:
    a: int
    b: str
    c: list[float]

class SQLAlchemyController(GenericController[ModelT]):
    @get()
    def get_handler(self, service: Callable[[], ModelT]) -> ModelT:
        return service()

def get_a() -> DC:
    return DC(a=1, b="two", c=[3.0, 4.0])

class AController(SQLAlchemyController[DC]):
    dependencies = {"service": Provide(lambda: get_a)}

app = Starlite(route_handlers=[AController], openapi_config=None)
"""
    )
    with TestClient(app=module.app) as client:
        resp = client.get("/")
        assert resp.json() == {"a": 1, "b": "two", "c": [3.0, 4.0]}
