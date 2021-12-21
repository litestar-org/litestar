from inspect import Signature, getfullargspec
from typing import Any, Callable, Dict, Tuple, Type

from pydantic import BaseConfig, BaseModel, create_model
from pydantic_factories import ModelFactory

from starlite.exceptions import ImproperlyConfiguredException


def create_function_signature_model(fn: Callable) -> Type[BaseModel]:
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
            if ModelFactory.is_constrained_field(parameter.default):
                field_definitions[key] = (parameter.default, ...)
            elif parameter.default is not signature.empty:
                field_definitions[key] = (value, parameter.default)
            elif not repr(parameter.annotation).startswith("typing.Optional"):
                field_definitions[key] = (value, ...)
            else:
                field_definitions[key] = (value, None)
        name = (fn.__name__ if hasattr(fn, "__name__") else "anonymous") + "SignatureModel"
        return create_model(name, __config__=Config, **field_definitions)
    except TypeError as e:
        raise ImproperlyConfiguredException("Unsupported callable passed to Provide") from e
