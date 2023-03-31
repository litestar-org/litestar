from __future__ import annotations

from abc import ABCMeta
from typing import TYPE_CHECKING, Generic, TypeVar, cast

from pydantic import BaseModel, parse_obj_as
from typing_extensions import get_args

from starlite.constants import UNDEFINED_SENTINELS
from starlite.dto import DataT
from starlite.dto.factory import AbstractDTOFactory
from starlite.dto.factory.config import DTO_FIELD_META_KEY
from starlite.dto.factory.types import FieldDefinition
from starlite.dto.factory.utils import get_model_type_hints

from .backend import PydanticDTOBackend

if TYPE_CHECKING:
    from typing import Any, ClassVar, Generator, Iterable

    from typing_extensions import Self

    from starlite.connection import Request
    from starlite.enums import MediaType

__all__ = ("PydanticBackedDTOFactory", "PydanticDTO")


PydanticDataT = TypeVar("PydanticDataT", bound="BaseModel | Iterable[BaseModel]")


class PydanticBackedDTOFactory(AbstractDTOFactory[DataT], Generic[DataT], metaclass=ABCMeta):
    dto_backend_type = PydanticDTOBackend
    dto_backend: ClassVar[PydanticDTOBackend]


class PydanticDTO(PydanticBackedDTOFactory[PydanticDataT], Generic[PydanticDataT]):
    __slots__ = ()

    model_type: ClassVar[type[BaseModel]]

    @classmethod
    def generate_field_definitions(cls, model_type: type[BaseModel]) -> Generator[FieldDefinition, None, None]:
        fields = model_type.__fields__
        for key, type_hint in get_model_type_hints(model_type).items():
            if not (field := fields.get(key)):
                continue

            field_def = FieldDefinition(
                field_name=key, field_type=type_hint, dto_field=field.field_info.extra.get(DTO_FIELD_META_KEY)
            )

            if field.default not in UNDEFINED_SENTINELS:
                field_def.default = field.default

            if field.default_factory is not None:
                field_def.default_factory = field.default_factory

            yield field_def

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        if args := get_args(field_definition.field_type):
            return any(issubclass(a, BaseModel) for a in args)
        return issubclass(field_definition.field_type, BaseModel)

    @classmethod
    async def from_connection(cls, connection: Request[Any, Any, Any]) -> Self:
        """Construct an instance from bytes.

        Args:
            connection: A byte representation of the DTO model.

        Returns:
            AbstractDTOFactory instance.
        """
        parsed = cls.dto_backend.parse_raw(await connection.body(), connection.content_type[0])
        return cls(data=parse_obj_as(cls.annotation, parsed))

    def to_encodable_type(
        self, media_type: str | MediaType, request: Request[Any, Any, Any]
    ) -> BaseModel | Iterable[BaseModel]:
        if isinstance(self.data, self.model_type):
            return self.dto_backend.data_container_type.parse_obj(self.data.dict())
        data = cast("Iterable[BaseModel]", self.data)
        return parse_obj_as(  # type:ignore[return-value]
            self.dto_backend.annotation, [datum.dict() for datum in data]
        )
