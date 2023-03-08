from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from typing_extensions import get_args

from starlite.enums import MediaType
from starlite.exceptions import SerializationException
from starlite.new_dto import AbstractDTO
from starlite.serialization import decode_json, decode_msgpack

if TYPE_CHECKING:
    from typing import Any

    from typing_extensions import Self

    from starlite.types.protocols import DataclassProtocol


@dataclass(unsafe_hash=True)
class Model:
    a: int
    b: str


def create_model_instance() -> Model:
    return Model(a=1, b="two")


SupportedT = TypeVar("SupportedT", bound="DataclassProtocol | Iterable[DataclassProtocol]")


class ConcreteDTO(AbstractDTO[SupportedT], Generic[SupportedT]):
    def to_encodable_type(self, _: str | MediaType) -> SupportedT:
        return self.data

    @classmethod
    def from_bytes(cls, raw: bytes, media_type: MediaType | str = MediaType.JSON) -> Self:
        if media_type == MediaType.JSON:
            data = decode_json(raw, cls.annotation)
        elif media_type == MediaType.MESSAGEPACK:
            data = decode_msgpack(raw, cls.annotation)
        else:
            raise SerializationException(f"Unsupported media type: '{media_type}'")
        return cls(data)

    @classmethod
    def supports_type(cls, value: type) -> bool:
        if issubclass(value, Iterable):
            if not (args := get_args(value)):
                return False
            value = args[0]
        return issubclass(value, Model)
