from inspect import Signature, getfullargspec, isclass
from typing import Any, Dict, Tuple, Type, cast

from pydantic import BaseConfig, BaseModel, create_model
from pydantic.fields import ModelField
from pydantic.typing import AnyCallable
from pydantic_factories import ModelFactory
from pydantic_factories.utils import create_model_from_dataclass

from starlite.exceptions import ImproperlyConfiguredException


def create_function_signature_model(fn: AnyCallable) -> Type[BaseModel]:
    """
    Creates a pydantic model for the signature of a given function
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    try:
        signature = Signature.from_callable(fn)
        field_definitions: Dict[str, Tuple[Any, Any]] = {}
        for key, value in getfullargspec(fn).annotations.items():
            if key == "return":
                continue
            parameter = signature.parameters[key]
            if key == "request":
                field_definitions[key] = (Any, ...)
            elif ModelFactory.is_constrained_field(parameter.default):
                field_definitions[key] = (parameter.default, ...)
            elif parameter.default is not signature.empty:
                field_definitions[key] = (value, parameter.default)
            elif not repr(parameter.annotation).startswith("typing.Optional"):
                field_definitions[key] = (value, ...)
            else:
                field_definitions[key] = (value, None)
        name = (fn.__name__ if hasattr(fn, "__name__") else "anonymous") + "SignatureModel"
        return create_model(name, __config__=Config, **field_definitions)  # type: ignore
    except TypeError as e:
        raise ImproperlyConfiguredException(repr(e)) from e


def create_parsed_model_field(value: Type[Any]) -> ModelField:
    """Create a pydantic model with the passed in value as its sole field, and return the parsed field"""

    model = create_model("temp", **{"value": (value, ... if not repr(value).startswith("typing.Optional") else None)})  # type: ignore
    return cast(BaseModel, model).__fields__["value"]


_dataclass_model_map: Dict[Any, Type[BaseModel]] = {}


def convert_dataclass_to_model(dataclass: Any) -> Type[BaseModel]:
    """Converts a dataclass to a pydantic model and memoizes the result"""
    if not isclass(dataclass) and hasattr(dataclass, "__class__"):
        dataclass = dataclass.__class__
    if not _dataclass_model_map.get(dataclass):
        _dataclass_model_map[dataclass] = create_model_from_dataclass(dataclass)
    return _dataclass_model_map[dataclass]
