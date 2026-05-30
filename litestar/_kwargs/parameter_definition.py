from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import ParameterKwarg

if TYPE_CHECKING:
    from litestar.enums import ParamType
    from litestar.typing import FieldDefinition


__all__ = ("ParameterDefinition", "create_parameter_definition", "merge_parameter_sets")


class ParameterDefinition(NamedTuple):
    """Tuple defining a kwarg representing a request parameter."""

    default: Any
    field_alias: str
    field_name: str
    is_required: bool
    is_sequence: bool
    param_type: ParamType


def create_parameter_definition(
    field_definition: FieldDefinition,
    field_name: str,
    path_parameters: set[str],
) -> ParameterDefinition | None:
    """Create a ParameterDefinition for the given FieldDefinition.

    Args:
        field_definition: FieldDefinition instance.
        field_name: The field's name.
        path_parameters: A set of path parameter names.

    Returns:
        A ParameterDefinition tuple.
    """
    kwarg_definition = (
        field_definition.kwarg_definition if isinstance(field_definition.kwarg_definition, ParameterKwarg) else None
    )

    if kwarg_definition is None:
        raise ImproperlyConfiguredException()

    param_type = kwarg_definition.param_type
    field_alias = kwarg_definition.name or field_name

    return ParameterDefinition(
        param_type=param_type,
        field_name=field_name,
        field_alias=field_alias,
        default=field_definition.default,
        is_required=field_definition.is_required and not field_definition.is_optional and not field_definition.is_any,
        is_sequence=field_definition.is_non_string_sequence,
    )


def merge_parameter_sets(first: set[ParameterDefinition], second: set[ParameterDefinition]) -> set[ParameterDefinition]:
    """Given two sets of parameter definitions, coming from different dependencies for example, merge them into a single
    set.
    """
    result: set[ParameterDefinition] = first.intersection(second)
    difference = first.symmetric_difference(second)
    for param in difference:
        # add the param if it's either required or no-other param in difference is the same but required
        if param.is_required or not any(p.field_alias == param.field_alias and p.is_required for p in difference):
            result.add(param)
    return result
