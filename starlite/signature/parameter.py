from inspect import Parameter, Signature
from typing import Any

from msgspec._core import nodefault as MsgspecUndefined
from pydantic.fields import Undefined as PydanticUndefined

from starlite.params import Dependency, DependencyKwarg, ParameterKwarg, BodyKwarg
from starlite.exceptions import ImproperlyConfiguredException
from starlite.types import Empty
from starlite.utils import is_optional_union

UNDEFINED_SENTINELS = {PydanticUndefined, Signature.empty, MsgspecUndefined, Empty}
SKIP_VALIDATION_NAMES = {"request", "socket", "scope", "receive", "send"}


class SignatureParameter:
    """Represents the parameters of a callable for purpose of signature model generation."""

    __slots__ = (
        "annotation",
        "default",
        "name",
        "optional",
    )

    annotation: Any
    default: Any
    name: str
    optional: bool

    def __init__(self, fn_name: str, parameter_name: str, parameter: Parameter) -> None:
        """Initialize SignatureParameter.

        Args:
            fn_name: Name of function.
            parameter_name: Name of parameter.
            parameter: inspect.Parameter
        """
        if parameter.annotation is Signature.empty:
            raise ImproperlyConfiguredException(
                f"Kwarg {parameter_name} of {fn_name} does not have a type annotation. If it "
                f"should receive any value, use the 'Any' type."
            )
        self.annotation = parameter.annotation
        self.default = parameter.default
        self.name = parameter_name
        self.optional = is_optional_union(parameter.annotation)

    @property
    def default_defined(self) -> bool:
        """Whether a default value is defined for the parameter.

        Returns:
            A boolean determining whether a default value is defined.
        """
        return isinstance(self.default, (ParameterKwarg, DependencyKwarg, BodyKwarg)) or self.default not in UNDEFINED_SENTINELS

    @property
    def should_skip_validation(self) -> bool:
        """Whether the parameter should skip validation.

        Returns:
            A boolean indicating whether the parameter should be validated.
        """
        return self.name in SKIP_VALIDATION_NAMES or (isinstance(self.default, DependencyKwarg) and self.default.skip_validation)
