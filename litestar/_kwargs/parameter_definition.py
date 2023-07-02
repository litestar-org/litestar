from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from litestar.enums import ParamType
from litestar.params import ParameterKwarg

__all__ = ("ParameterDefinition", "create_parameter_definition", "merge_parameter_sets")


if TYPE_CHECKING:
    from litestar.typing import ParsedType


class ParameterDefinition(NamedTuple):
    """Tuple defining a kwarg representing a request parameter."""

    default: Any
    field_alias: str
    field_name: str
    is_required: bool
    is_sequence: bool
    param_type: ParamType


def create_parameter_definition(
    parsed_type: ParsedType,
    field_name: str,
    path_parameters: set[str],
) -> ParameterDefinition:
    """Create a ParameterDefinition for the given ParsedType.

    Args:
        parsed_type: ParsedType instance.
        field_name: The field's name.
        path_parameters: A set of path parameter names.

    Returns:
        A ParameterDefinition tuple.
    """
    default = None if not parsed_type.has_default else parsed_type.default
    kwargs_model = parsed_type.kwarg_model if isinstance(parsed_type.kwarg_model, ParameterKwarg) else None

    field_alias = kwargs_model.query if kwargs_model and kwargs_model.query else field_name
    param_type = ParamType.QUERY

    if field_name in path_parameters:
        field_alias = field_name
        param_type = ParamType.PATH
    elif kwargs_model and kwargs_model.header:
        field_alias = kwargs_model.header
        param_type = ParamType.HEADER
    elif kwargs_model and kwargs_model.cookie:
        field_alias = kwargs_model.cookie
        param_type = ParamType.COOKIE

    return ParameterDefinition(
        param_type=param_type,
        field_name=field_name,
        field_alias=field_alias,
        default=default,
        is_required=parsed_type.is_required
        and default is None
        and not parsed_type.is_optional
        and not parsed_type.is_any,
        is_sequence=parsed_type.is_non_string_sequence,
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
