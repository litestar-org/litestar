from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from starlite.enums import MediaType
from starlite.exceptions import SerializationException
from starlite.new_dto import AbstractDTO
from starlite.utils.predicates import is_class_and_subclass

if TYPE_CHECKING:
    from typing import Any, Iterable

    from typing_extensions import Self


@dataclass
class Model:
    a: int
    b: str


class ConcreteDTO(AbstractDTO[Model]):
    def to_bytes(self, media_type: MediaType | str = MediaType.JSON) -> bytes:
        if media_type == MediaType.JSON:
            return b'{"a":1,"b":"two"}'
        if media_type == MediaType.MESSAGEPACK:
            return b"\x82\xa1a\x01\xa1b\xa3two"
        raise SerializationException(f"Media type '{media_type}' not supported by DTO.")

    def to_model(self) -> Model:
        return Model(a=1, b="two")

    @classmethod
    def encode_iterable(cls, value: Iterable[Self], media_type: MediaType | str = MediaType.JSON) -> bytes:
        if media_type == MediaType.JSON:
            return b'[{"a":1,"b":"two"},{"a":3,"b":"four"}]'
        if media_type == MediaType.MESSAGEPACK:
            return b"\x92\x82\xa1a\x01\xa1b\xa3two\x82\xa1a\x03\xa1b\xa4four"
        raise SerializationException(f"Media type '{media_type}' not supported by DTO.")

    @classmethod
    def from_bytes(cls, raw: bytes) -> Self:
        return cls()

    @classmethod
    def list_from_bytes(cls, raw: bytes) -> list[Self]:
        return [cls(), cls()]

    @classmethod
    def from_model(cls, model: Model) -> Self:
        return cls()

    @classmethod
    def supports(cls, value: Any) -> bool:
        return is_class_and_subclass(value, Model) or isinstance(value, Model)
