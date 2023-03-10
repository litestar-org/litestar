from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseConfig, BaseModel, create_model, create_model_from_typeddict
from pydantic_factories.utils import create_model_from_dataclass

__all__ = ("Config", "convert_dataclass_to_model", "convert_typeddict_to_model", "create_parsed_model_field")


if TYPE_CHECKING:
    from pydantic.fields import ModelField

    from starlite.types.builtin_types import DataclassClassOrInstance, TypedDictClass


class Config(BaseConfig):
    """Base config for models."""

    arbitrary_types_allowed = True


def create_parsed_model_field(value: type[Any]) -> ModelField:
    """Create a pydantic model with the passed in value as its sole field, and return the parsed field."""
    model = create_model(
        "temp", __config__=Config, value=(value, ... if not repr(value).startswith("typing.Optional") else None)
    )

    return cast("BaseModel", model).__fields__["value"]


_type_model_map: dict[type[Any], type[BaseModel]] = {}


def convert_dataclass_to_model(dataclass_or_instance: DataclassClassOrInstance) -> type[BaseModel]:
    """Convert a dataclass or dataclass instance to a pydantic model and memoize the result."""
    dataclass = type(dataclass_or_instance) if not isinstance(dataclass_or_instance, type) else dataclass_or_instance

    existing = _type_model_map.get(dataclass)
    if not existing:
        _type_model_map[dataclass] = existing = create_model_from_dataclass(dataclass)  # type:ignore[arg-type]
    return existing


def convert_typeddict_to_model(typeddict: TypedDictClass) -> type[BaseModel]:
    """Convert a :class:`TypedDict <typing.TypedDict>` to a pydantic model and memoize the result."""
    existing = _type_model_map.get(typeddict)
    if not existing:
        _type_model_map[typeddict] = existing = create_model_from_typeddict(typeddict)
    return existing
