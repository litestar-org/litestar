from __future__ import annotations

from typing import Any, Generator, Generic, Optional, TypeVar

from _decimal import Decimal
from msgspec import Meta
from typing_extensions import Annotated

from litestar.dto.factory.abc import AbstractDTOFactory
from litestar.dto.factory.data_structures import FieldDefinition
from litestar.dto.factory.field import DTOField, Mark
from litestar.exceptions import MissingDependencyException
from litestar.types import Empty
from litestar.typing import ParsedType
from litestar.utils.helpers import get_fully_qualified_class_name

try:
    import piccolo  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("piccolo orm is not installed") from e

from piccolo.columns import Column, column_types
from piccolo.table import Table

T = TypeVar("T", bound=Table)

__all__ = ("PiccoloDTO",)


def _parse_piccolo_type(column: Column, extra: dict[str, Any]) -> ParsedType:
    if isinstance(column, (column_types.Decimal, column_types.Numeric)):
        column_type: Any = Decimal
        meta = Meta(extra=extra)
    elif isinstance(column, (column_types.Email, column_types.Varchar)):
        column_type = str
        meta = Meta(max_length=column.length, extra=extra)
    elif isinstance(column, column_types.Array):
        column_type = list[column.base_column.value_type]  # type: ignore
        meta = Meta(extra=extra)
    elif isinstance(column, (column_types.JSON, column_types.JSONB)):
        column_type = str
        meta = Meta(extra={**extra, "format": "json"})
    elif isinstance(column, column_types.Text):
        column_type = str
        meta = Meta(extra={**extra, "format": "text-area"})
    elif isinstance(column, column_types.Secret):
        column_type = str
        meta = Meta(extra={"secret": True})
    else:
        column_type = column.value_type
        meta = Meta(extra=extra)

    if not column._meta.required:
        column_type = Optional[column_type]

    return ParsedType(Annotated[column_type, meta])


def _create_column_extra(column: Column) -> dict[str, Any]:
    extra: dict[str, Any] = {}

    if column._meta.help_text:
        extra["help_text"] = column._meta.help_text

    if column._meta.get_choices_dict():
        extra["choices"] = column._meta.get_choices_dict()

    if column._meta.db_column_name != column._meta.name:
        extra["alias"] = column._meta.db_column_name

    if isinstance(column, column_types.ForeignKey):
        extra["foreign_key"] = True
        extra["to"] = column._foreign_key_meta.resolved_references._meta.tablename
        extra["target_column"] = column._foreign_key_meta.resolved_target_column._meta.name

    return extra


class PiccoloDTO(AbstractDTOFactory[T], Generic[T]):
    @classmethod
    def generate_field_definitions(cls, model_type: type[Table]) -> Generator[FieldDefinition, None, None]:
        unique_model_name = get_fully_qualified_class_name(model_type)

        for column in model_type._meta.columns:
            yield FieldDefinition(
                default=Empty if column._meta.required else None,
                default_factory=Empty,
                # TODO: is there a better way of handling this?
                dto_field=DTOField(mark=Mark.READ_ONLY if column._meta.primary_key else None),
                dto_for=None,
                name=column._meta.name,
                parsed_type=_parse_piccolo_type(column, _create_column_extra(column)),
                unique_model_name=unique_model_name,
            )

    @classmethod
    def detect_nested_field(cls, parsed_type: ParsedType) -> bool:
        return parsed_type.is_subclass_of(Table)
