from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from litestar.dto.factory._backends.utils import create_transfer_model_type_annotation
from litestar.types import Empty

if TYPE_CHECKING:
    from typing import Any

    from litestar.dto.factory._backends.types import FieldDefinitionsType, TransferFieldDefinition

__all__ = ("_create_model_for_field_definitions",)

ModelT = TypeVar("ModelT", bound=BaseModel)
T = TypeVar("T")


class _OrmModeBase(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        orm_mode = True


def _create_field_info(field_definition: TransferFieldDefinition) -> FieldInfo:
    kws: dict[str, Any] = {}
    if field_definition.default is not Empty:
        kws["default"] = field_definition.default
    elif field_definition.default_factory is not Empty:
        kws["default_factory"] = field_definition.default_factory
    else:
        kws["default"] = ...

    return FieldInfo(**kws)


def _create_model_for_field_definitions(model_name: str, field_definitions: FieldDefinitionsType) -> type[BaseModel]:
    model_fields: dict[str, tuple[type, FieldInfo]] = {}
    for field_def in field_definitions:
        model_fields[field_def.serialization_name] = (
            create_transfer_model_type_annotation(field_def.transfer_type),
            _create_field_info(field_def),
        )
    return create_model(
        model_name,
        __config__=None,
        __base__=_OrmModeBase,
        __module__=BaseModel.__module__,
        __validators__={},
        __cls_kwargs__={},
        **model_fields,
    )
