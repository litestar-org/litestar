from __future__ import annotations

from collections.abc import Collection as CollectionsCollection
from typing import TYPE_CHECKING, TypeVar, cast
from uuid import uuid4

from pydantic import BaseModel, parse_obj_as

from litestar.dto.factory.backends.abc import AbstractDTOBackend, BackendContext
from litestar.serialization import decode_media_type

from .utils import _build_data_from_pydantic_model, _create_model_for_field_definitions

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.connection import Request
    from litestar.dto.factory.types import FieldDefinitionsType
    from litestar.enums import MediaType
    from litestar.types.serialization import LitestarEncodableType

__all__ = ("PydanticDTOBackend",)


T = TypeVar("T")


class PydanticDTOBackend(AbstractDTOBackend[BaseModel]):
    __slots__ = ()

    def parse_raw(self, raw: bytes, media_type: MediaType | str) -> BaseModel | Collection[BaseModel]:
        return decode_media_type(raw, media_type, type_=self.annotation)  # type:ignore[no-any-return]

    def populate_data_from_builtins(self, model_type: type[T], data: Any) -> T | Collection[T]:
        parsed_data = cast("BaseModel | Collection[BaseModel]", parse_obj_as(self.annotation, data))
        return _build_data_from_pydantic_model(model_type, parsed_data, self.context.field_definitions)

    def populate_data_from_raw(self, model_type: type[T], raw: bytes, media_type: MediaType | str) -> T | Collection[T]:
        parsed_data = self.parse_raw(raw, media_type)
        return _build_data_from_pydantic_model(model_type, parsed_data, self.context.field_definitions)

    def encode_data(self, data: Any, connection: Request) -> LitestarEncodableType:
        if isinstance(data, CollectionsCollection):
            return self.context.parsed_type.origin(  # type:ignore[no-any-return]
                self.data_container_type.from_orm(datum) for datum in data  # pyright:ignore
            )
        return self.data_container_type.from_orm(data)

    @classmethod
    def from_field_definitions(cls, annotation: Any, field_definitions: FieldDefinitionsType) -> Any:
        context = BackendContext(annotation, field_definitions)
        return cls(context, _create_model_for_field_definitions(str(uuid4()), field_definitions))
