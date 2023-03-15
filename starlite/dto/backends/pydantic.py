from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseConfig, BaseModel, create_model
from pydantic.fields import FieldInfo

from starlite.dto.types import NestedFieldDefinition
from starlite.enums import MediaType
from starlite.exceptions import SerializationException
from starlite.types import Empty

from .abc import AbstractDTOBackend

__all__ = ["PydanticDTOBackend"]


if TYPE_CHECKING:
    from typing import Any

    from starlite.dto.types import FieldDefinition, FieldDefinitionsType


class PydanticDTOBackend(AbstractDTOBackend):
    def __init__(self, model: type[BaseModel]) -> None:
        self.model = model

    def raw_to_dict(self, raw: bytes, media_type: MediaType | str) -> dict[str, Any]:
        if media_type != MediaType.JSON:
            raise SerializationException(f"Unsupported media type: '{media_type}'")
        return self.model.parse_raw(raw).dict()

    @classmethod
    def from_field_definitions(cls, field_definitions: FieldDefinitionsType) -> Any:
        return cls(_create_pydantic_model_for_field_definitions(str(uuid4()), field_definitions))


def _create_pydantic_field_info(field_definition: FieldDefinition) -> FieldInfo:
    kws: dict[str, Any] = {}
    if field_definition.default is not Empty:
        kws["default"] = field_definition.default

    if field_definition.default_factory is not Empty:
        kws["default_factory"] = field_definition.default_factory

    return FieldInfo(**kws)


def _create_pydantic_model_for_field_definitions(
    model_name: str, field_definitions: FieldDefinitionsType
) -> type[BaseModel]:
    pydantic_fields: dict[str, tuple[type, FieldInfo]] = {}
    for k, v in field_definitions.items():
        if isinstance(v, NestedFieldDefinition):
            nested_pydantic_model = _create_pydantic_model_for_field_definitions(
                f"{k}.nested.{str(uuid4())}", v.nested_field_definitions
            )
            pydantic_fields[k] = (
                v.make_field_type(nested_pydantic_model),
                _create_pydantic_field_info(v.field_definition),
            )
        else:
            pydantic_fields[k] = (v.field_type, _create_pydantic_field_info(v))

    return create_model(
        model_name,
        __config__=type("Config", (BaseConfig,), {"orm_mode": True}),
        __base__=None,
        __module__=BaseModel.__module__,
        __validators__={},
        __cls_kwargs__={},
        **pydantic_fields,
    )
