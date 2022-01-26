from inspect import Signature
from typing import Any, ClassVar, Dict, List, Type, cast

from pydantic import BaseConfig, BaseModel, create_model
from pydantic.fields import Undefined
from pydantic.typing import AnyCallable
from pydantic_factories import ModelFactory
from typing_extensions import get_args

from starlite.exceptions import ImproperlyConfiguredException
from starlite.plugins.base import PluginMapping, PluginProtocol, get_plugin_for_value


class SignatureModel(BaseModel):
    class Config(BaseConfig):
        arbitrary_types_allowed = True

    field_plugin_mappings: ClassVar[Dict[str, PluginMapping]]
    return_annotation: ClassVar[Any]


def model_function_signature(fn: AnyCallable, plugins: List[PluginProtocol]) -> Type[SignatureModel]:
    """
    Creates a subclass of SignatureModel for the signature of a given function
    """

    try:
        signature = Signature.from_callable(fn)
        field_plugin_mappings: Dict[str, PluginMapping] = {}
        field_definitions: Dict[str, Any] = {}
        fn_name = fn.__name__ if hasattr(fn, "__name__") else "anonymous"
        defaults: Dict[str, Any] = {}
        for kwarg, parameter in list(signature.parameters.items()):
            if kwarg in ["self", "cls"]:
                continue
            type_annotation = parameter.annotation
            if type_annotation is signature.empty:
                raise ImproperlyConfiguredException(
                    f"kwarg {kwarg} of {fn_name} does not have a type annotation. If it should receive any value, use the 'Any' type."
                )
            if kwarg in ["request", "socket"]:
                # pydantic has issues with none-pydantic classes that receive generics
                field_definitions[kwarg] = (Any, ...)
                continue
            default = parameter.default
            if ModelFactory.is_constrained_field(default):
                field_definitions[kwarg] = (default, ...)
                continue
            plugin = get_plugin_for_value(value=type_annotation, plugins=plugins)
            if plugin:
                type_args = get_args(type_annotation)
                type_value = type_args[0] if type_args else type_annotation
                field_plugin_mappings[kwarg] = PluginMapping(plugin=plugin, model_class=type_value)
                pydantic_model = plugin.to_pydantic_model_class(model_class=type_value)
                if type_args:
                    type_annotation = List[pydantic_model]  # type: ignore
                else:
                    type_annotation = pydantic_model
            if default not in [signature.empty, Undefined]:
                field_definitions[kwarg] = (type_annotation, default)
                defaults[kwarg] = default
            elif not repr(parameter.annotation).startswith("typing.Optional"):
                field_definitions[kwarg] = (type_annotation, ...)
            else:
                field_definitions[kwarg] = (type_annotation, None)
        model: Type[SignatureModel] = create_model(
            fn_name + "_signature_model", __base__=SignatureModel, **field_definitions
        )
        model.return_annotation = signature.return_annotation
        model.field_plugin_mappings = field_plugin_mappings
        return model
    except TypeError as e:
        raise ImproperlyConfiguredException(repr(e)) from e


def get_signature_model(value: Any) -> Type[SignatureModel]:
    """
    Helper function to retrieve and validate the signature model from a provider or handler
    """
    try:
        return cast(Type[SignatureModel], getattr(value, "signature_model"))
    except AttributeError as e:  # pragma: no cover
        raise ImproperlyConfiguredException(f"The 'signature_model' attribute for {value} is not set") from e
