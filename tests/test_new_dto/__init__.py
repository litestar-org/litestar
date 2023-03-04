from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from starlite.new_dto import AbstractDTO

if TYPE_CHECKING:
    from typing_extensions import Self


@dataclass
class Model:
    a: int
    b: str


class ConcreteDTO(AbstractDTO[Model]):
    def to_bytes(self) -> bytes:
        return b'{"a":1,"b":"two"}'

    def to_model(self) -> Model:
        return Model(a=1, b="two")

    @classmethod
    def from_bytes(cls, raw: bytes) -> Self:
        return cls()

    @classmethod
    def list_from_bytes(cls, raw: bytes) -> list[Self]:
        return [cls(), cls()]

    @classmethod
    def from_model(cls, model: Model) -> Self:
        return cls()
