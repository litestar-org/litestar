from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from litestar.constants import SKIP_VALIDATION_NAMES
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import DependencyKwarg
from litestar.types import Empty

if TYPE_CHECKING:
    from litestar.utils.signature import ParsedSignature

    from .model import SignatureModel

__all__ = ("create_type_overrides", "validate_signature_dependencies", "get_signature_model")


def get_signature_model(value: Any) -> type[SignatureModel]:
    """Retrieve and validate the signature model from a provider or handler."""
    try:
        return cast("type[SignatureModel]", value.signature_model)
    except AttributeError as e:  # pragma: no cover
        raise ImproperlyConfiguredException(f"The 'signature_model' attribute for {value} is not set") from e


def create_type_overrides(parsed_signature: ParsedSignature, has_data_dto: bool) -> dict[str, Any]:
    """Create typing overrides for field definitions.

    Args:
        parsed_signature: A parsed function signature.
        has_data_dto: Whether the signature contains a data DTO.

    Returns:
        A dictionary of typing overrides
    """
    type_overrides = {}
    for field_definition in parsed_signature.parameters.values():
        if field_definition.name in SKIP_VALIDATION_NAMES or (
            isinstance(field_definition.kwarg_definition, DependencyKwarg)
            and field_definition.kwarg_definition.skip_validation
        ):
            type_overrides[field_definition.name] = Any

        if has_data_dto and "data" in parsed_signature.parameters:
            type_overrides["data"] = Any

    return type_overrides


def validate_signature_dependencies(
    dependency_name_set: set[str], fn_name: str, parsed_signature: ParsedSignature
) -> set[str]:
    """Validate dependencies of ``parsed_signature``.

    Args:
        dependency_name_set: A set of dependency names
        fn_name: A callable's name.
        parsed_signature: A parsed signature.

    Returns:
        A set of validated dependency names.
    """
    dependency_names: set[str] = set(dependency_name_set)

    for parameter in parsed_signature.parameters.values():
        if isinstance(parameter.kwarg_definition, DependencyKwarg) and parameter.name not in dependency_name_set:
            if not parameter.is_optional and parameter.default is Empty:
                raise ImproperlyConfiguredException(
                    f"Explicit dependency '{parameter.name}' for '{fn_name}' has no default value, "
                    f"or provided dependency."
                )
            dependency_names.add(parameter.name)
    return dependency_names
