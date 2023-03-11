from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from starlite.dto import AbstractDTO
from starlite.enums import MediaType
from starlite.exceptions import SerializationException
from starlite.serialization import decode_json, decode_msgpack

if TYPE_CHECKING:
    from typing import Iterable

    from typing_extensions import Self

    from starlite.dto.types import FieldDefinitionsType
    from starlite.types.protocols import DataclassProtocol


@dataclass(unsafe_hash=True)
class Model:
    a: int
    b: str


def create_model_instance() -> Model:
    return Model(a=1, b="two")


SupportedT = TypeVar("SupportedT", bound="DataclassProtocol | Iterable[DataclassProtocol]")


class ExampleDTO(AbstractDTO[SupportedT], Generic[SupportedT]):
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
    def parse_model(cls) -> FieldDefinitionsType:
        return {"a": (int, ...), "b": (str, ...)}
