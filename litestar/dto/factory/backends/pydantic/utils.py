from __future__ import annotations

from collections.abc import Collection as CollectionsCollection
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from litestar.dto.factory.types import NestedFieldDefinition
from litestar.types import Empty

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.dto.factory.types import FieldDefinition, FieldDefinitionsType

__all__ = ("_create_model_for_field_definitions", "_build_data_from_pydantic_model")

ModelT = TypeVar("ModelT", bound=BaseModel)
T = TypeVar("T")


class _OrmModeBase(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        orm_mode = True


def _create_field_info(field_definition: FieldDefinition) -> FieldInfo:
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
    for k, v in field_definitions.items():
        if isinstance(v, NestedFieldDefinition):
            nested_model = _create_model_for_field_definitions(f"{model_name}.{k}", v.nested_field_definitions)
            model_fields[k] = (v.make_field_type(nested_model), _create_field_info(v.field_definition))
        else:
            model_fields[k] = (v.parsed_type.annotation, _create_field_info(v))
    return create_model(
        model_name,
        __config__=None,
        __base__=_OrmModeBase,
        __module__=BaseModel.__module__,
        __validators__={},
        __cls_kwargs__={},
        **model_fields,
    )


def _build_model_from_pydantic_model(
    model_type: type[T], data: BaseModel, field_definitions: FieldDefinitionsType
) -> T:
    """Create instance of ``model_type``.

    Args:
        model_type: the model type received by the DTO on type narrowing.
        data: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.

    Returns:
        Data parsed into ``model_type``.
    """
    unstructured_data = {}
    for k in data.__fields__:
        v = getattr(data, k)

        field = field_definitions[k]

        if isinstance(field, NestedFieldDefinition) and isinstance(v, CollectionsCollection):
            parsed_type = field.field_definition.parsed_type
            if parsed_type.origin is None:  # pragma: no cover
                raise RuntimeError("Unexpected origin value for collection type.")
            unstructured_data[k] = parsed_type.origin(
                _build_model_from_pydantic_model(field.nested_type, item, field.nested_field_definitions) for item in v
            )
        elif isinstance(field, NestedFieldDefinition) and isinstance(v, BaseModel):
            unstructured_data[k] = _build_model_from_pydantic_model(
                field.nested_type, v, field.nested_field_definitions
            )
        else:
            unstructured_data[k] = v

    return model_type(**unstructured_data)


def _build_data_from_pydantic_model(
    model_type: type[T], data: BaseModel | Collection[BaseModel], field_definitions: FieldDefinitionsType
) -> T | Collection[T]:
    """Create instance or iterable of instances of ``model_type``.

    Args:
        model_type: the model type received by the DTO on type narrowing.
        data: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.

    Returns:
        Data parsed into ``model_type``.
    """
    if isinstance(data, CollectionsCollection):
        return type(data)(  # type:ignore[return-value]
            _build_data_from_pydantic_model(model_type, item, field_definitions)
            for item in data  # type:ignore[call-arg]
        )
    return _build_model_from_pydantic_model(model_type, data, field_definitions)
