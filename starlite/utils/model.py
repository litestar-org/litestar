from inspect import Signature, getfullargspec, isclass
from typing import Any, Dict, List, Type, cast, get_args

from pydantic import BaseConfig, BaseModel, create_model
from pydantic.fields import ModelField
from pydantic.typing import AnyCallable
from pydantic_factories import ModelFactory
from pydantic_factories.utils import create_model_from_dataclass

from starlite.exceptions import ImproperlyConfiguredException
from starlite.plugins.base import PluginMapping, PluginProtocol, get_plugin_for_value


def create_function_signature_model(fn: AnyCallable, plugins: List[PluginProtocol]) -> Type[BaseModel]:
    """
    Creates a pydantic model for the signature of a given function
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    try:
        signature = Signature.from_callable(fn)
        field_definitions: Dict[str, Any] = {
            # return type annotation
            "_return_annotation": (signature.return_annotation, None),
            # mapping for plugin values
            "_field_plugin_mappings": {},
        }
        for key, value in getfullargspec(fn).annotations.items():
            if key == "return":
                continue
            parameter = signature.parameters[key]
            if key in ["request", "socket"]:
                # pydantic has issues with none-pydantic classes that receive generics
                field_definitions[key] = (Any, ...)
                continue
            if ModelFactory.is_constrained_field(parameter.default):
                field_definitions[key] = (parameter.default, ...)
                continue
            plugin = get_plugin_for_value(value=value, plugins=plugins)
            if plugin:
                type_args = get_args(value)
                type_value = type_args[0] if type_args else value
                field_definitions["_field_plugin_mappings"][key] = PluginMapping(plugin=plugin, model_class=type_value)
                pydantic_model = plugin.to_pydantic_model_class(model_class=type_value)
                if type_args:
                    value = List[pydantic_model]
                else:
                    value = pydantic_model
            if parameter.default is not signature.empty:
                field_definitions[key] = (value, parameter.default)
            elif not repr(parameter.annotation).startswith("typing.Optional"):
                field_definitions[key] = (value, ...)
            else:
                field_definitions[key] = (value, None)
        name = (fn.__name__ if hasattr(fn, "__name__") else "anonymous") + "_signature_model"
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
