from __future__ import annotations

from dataclasses import dataclass
from inspect import Parameter, Signature
from typing import Any

from litestar.constants import SKIP_VALIDATION_NAMES, UNDEFINED_SENTINELS
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from litestar.utils import is_optional_union

__all__ = ("ParsedSignatureParameter",)


@dataclass
class ParsedSignatureParameter:
    """Represents the parameters of a callable for purpose of signature model generation."""

    annotation: Any
    default: Any
    name: str
    optional: bool

    @classmethod
    def from_parameter(
        cls, fn_name: str, parameter_name: str, parameter: Parameter, fn_type_hints: dict[str, Any]
    ) -> ParsedSignatureParameter:
        """Initialize ParsedSignatureParameter.

        Args:
            fn_name: Name of function.
            parameter_name: Name of parameter.
            parameter: inspect.Parameter
            fn_type_hints: mapping of names to types for resolution of forward references.

        Returns:
            ParsedSignatureParameter.
        """
        if parameter.annotation is Signature.empty:
            raise ImproperlyConfiguredException(
                f"Kwarg {parameter_name} of {fn_name} does not have a type annotation. If it "
                f"should receive any value, use the 'Any' type."
            )

        annotation: Any = parameter.annotation
        if isinstance(annotation, str) and parameter_name in fn_type_hints:
            annotation = fn_type_hints[parameter_name]

        return ParsedSignatureParameter(
            annotation=annotation,
            default=parameter.default,
            name=parameter_name,
            optional=is_optional_union(parameter.annotation),
        )

    @property
    def default_defined(self) -> bool:
        """Whether a default value is defined for the parameter.

        Returns:
            A boolean determining whether a default value is defined.
        """
        return (
            isinstance(self.default, (ParameterKwarg, DependencyKwarg, BodyKwarg))
            or self.default not in UNDEFINED_SENTINELS
        )

    @property
    def should_skip_validation(self) -> bool:
        """Whether the parameter should skip validation.

        Returns:
            A boolean indicating whether the parameter should be validated.
        """
        return self.name in SKIP_VALIDATION_NAMES or (
            isinstance(self.default, DependencyKwarg) and self.default.skip_validation
        )
