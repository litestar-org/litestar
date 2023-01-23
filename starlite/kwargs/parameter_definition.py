from typing import TYPE_CHECKING, Any, NamedTuple, Set

from starlite.enums import ParamType
from starlite.params import ParameterKwarg

if TYPE_CHECKING:
    from starlite.signature.models import SignatureField


class ParameterDefinition(NamedTuple):
    """Tuple defining a kwarg representing a request parameter."""

    default_value: Any
    field_alias: str
    field_name: str
    is_required: bool
    is_sequence: bool
    param_type: ParamType


def create_parameter_definition(
    signature_field: "SignatureField",
    field_name: str,
    path_parameters: Set[str],
) -> ParameterDefinition:
    """Create a ParameterDefinition for the given SignatureField.

    Args:
        signature_field: SignatureField instance.
        field_name: The field's name.
        path_parameters: A set of path parameter names.

    Returns:
        A ParameterDefinition tuple.
    """
    default_value = signature_field.default_value if not signature_field.is_empty else None
    kwargs_model = signature_field.kwarg_model if isinstance(signature_field.kwarg_model, ParameterKwarg) else None

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
        default_value=default_value,
        is_required=signature_field.is_required
        and (default_value is None and not (signature_field.is_optional or signature_field.is_any)),
        is_sequence=signature_field.is_non_string_sequence,
    )


def merge_parameter_sets(first: Set[ParameterDefinition], second: Set[ParameterDefinition]) -> Set[ParameterDefinition]:
    """Given two sets of parameter definitions, coming from different dependencies for example, merge them into a single
    set.
    """
    result: Set[ParameterDefinition] = first.intersection(second)
    difference = first.symmetric_difference(second)
    for param in difference:
        # add the param if it's either required or no-other param in difference is the same but required
        if param.is_required or not any(p.field_alias == param.field_alias and p.is_required for p in difference):
            result.add(param)
    return result
