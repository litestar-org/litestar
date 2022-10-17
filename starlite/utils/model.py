from typing import TYPE_CHECKING, Any, Dict, Type, cast

from pydantic import BaseConfig, BaseModel, create_model, create_model_from_typeddict
from pydantic_factories.utils import create_model_from_dataclass

if TYPE_CHECKING:
    from pydantic.fields import ModelField

    from starlite.types.builtin_types import DataclassTypeOrInstance, TypedDictType


class Config(BaseConfig):
    arbitrary_types_allowed = True


def create_parsed_model_field(value: Type[Any]) -> "ModelField":
    """Create a pydantic model with the passed in value as its sole field, and
    return the parsed field."""
    model = create_model("temp", __config__=Config, **{"value": (value, ... if not repr(value).startswith("typing.Optional") else None)})  # type: ignore
    return cast("BaseModel", model).__fields__["value"]


_type_model_map: Dict[Type[Any], Type[BaseModel]] = {}


def convert_dataclass_to_model(dataclass_or_instance: "DataclassTypeOrInstance") -> Type[BaseModel]:
    """Converts a dataclass or dataclass instance to a pydantic model and
    memoizes the result."""

    if not isinstance(dataclass_or_instance, type):
        dataclass = type(dataclass_or_instance)
    else:
        dataclass = dataclass_or_instance

    existing = _type_model_map.get(dataclass)
    if not existing:
        _type_model_map[dataclass] = existing = create_model_from_dataclass(dataclass)
    return existing


def convert_typeddict_to_model(typeddict: "TypedDictType") -> Type[BaseModel]:
    """Converts a typeddict to a pydantic model and memoizes the result."""
    existing = _type_model_map.get(typeddict)
    if not existing:
        _type_model_map[typeddict] = existing = create_model_from_typeddict(typeddict)
    return existing
