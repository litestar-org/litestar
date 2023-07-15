from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, Union

from msgspec import UNSET, UnsetType
from pydantic import VERSION, BaseModel, create_model
from pydantic.fields import FieldInfo

from litestar.dto.factory._backends.utils import create_transfer_model_type_annotation
from litestar.types import Empty

if TYPE_CHECKING:
    from typing import Any

    from litestar.dto.factory._backends.types import FieldDefinitionsType, TransferDTOFieldDefinition

__all__ = ("_create_model_for_field_definitions",)

ModelT = TypeVar("ModelT", bound=BaseModel)
T = TypeVar("T")


class _OrmModeBase(BaseModel):
    if VERSION.startswith("1"):

        class Config:
            arbitrary_types_allowed = True
            orm_mode = True

    else:
        model_config = {"arbitrary_types_allowed": True, "from_attributes": True}


def _create_field_info(field_definition: TransferDTOFieldDefinition) -> FieldInfo:
    kws: dict[str, Any] = {}
    if field_definition.is_partial:
        kws["default"] = UNSET
    elif field_definition.default is not Empty:
        kws["default"] = field_definition.default
    elif field_definition.default_factory is not Empty:
        kws["default_factory"] = field_definition.default_factory
    else:
        kws["default"] = ...

    return FieldInfo(**kws)


def _create_model_for_field_definitions(model_name: str, field_definitions: FieldDefinitionsType) -> type[BaseModel]:
    model_fields: dict[str, tuple[type, FieldInfo]] = {}
    for field_def in field_definitions:
        if field_def.is_excluded:
            continue

        field_type = create_transfer_model_type_annotation(field_def.transfer_type)
        if field_def.is_partial:
            field_type = Union[field_type, UnsetType]

        model_fields[field_def.serialization_name] = (field_type, _create_field_info(field_def))

    return create_model(
        model_name,
        __config__=None,
        __base__=_OrmModeBase,
        __module__=BaseModel.__module__,
        __validators__={},
        __cls_kwargs__={},
        **model_fields,
    )
