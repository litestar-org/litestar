from typing import TYPE_CHECKING, Dict, List, Tuple

from pydantic_openapi_schema.v3_1_0.parameter import Parameter

from starlite.constants import RESERVED_KWARGS
from starlite.enums import ParamType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.openapi.schema import create_schema
from starlite.params import DependencyKwarg, ParameterKwarg
from starlite.signature.models import SignatureField
from starlite.types import Empty

if TYPE_CHECKING:
    from pydantic_openapi_schema.v3_1_0.schema import Schema

    from starlite.handlers import BaseRouteHandler
    from starlite.types import Dependencies
    from starlite.types.internal_types import PathParameterDefinition


def create_path_parameter_schema(
    path_parameter: "PathParameterDefinition", field: "SignatureField", generate_examples: bool
) -> "Schema":
    """Create a path parameter from the given path_param definition."""
    return create_schema(
        field=SignatureField(
            name=field.name,
            field_type=path_parameter.type,
            children=None,
            extra=field.extra,
            kwarg_model=field.kwarg_model,
            default_value=field.default_value,
        ),
        generate_examples=generate_examples,
        plugins=[],
    )


class ParameterCollection:
    """Facilitates conditional deduplication of parameters.

    If multiple parameters with the same name are produced for a handler, the condition is ignored if the two
    ``Parameter`` instances are the same (the first is retained and any duplicates are ignored). If the ``Parameter``
    instances are not the same, an exception is raised.
    """

    def __init__(self, route_handler: "BaseRouteHandler") -> None:
        """Initialize ``ParameterCollection``.

        Args:
            route_handler: Associated route handler
        """
        self.route_handler = route_handler
        self._parameters: Dict[str, Parameter] = {}

    def add(self, parameter: Parameter) -> None:
        """Add a ``Parameter`` to the collection.

        If an existing parameter with the same name and type already exists, the
        parameter is ignored.

        If an existing parameter with the same name but different type exists, raises
        ``ImproperlyConfiguredException``.
        """
        if parameter.name not in self._parameters:
            self._parameters[parameter.name] = parameter
            return

        pre_existing = self._parameters[parameter.name]
        if parameter == pre_existing:
            return

        raise ImproperlyConfiguredException(
            f"OpenAPI schema generation for handler `{self.route_handler}` detected multiple parameters named "
            f"'{parameter.name}' with different types."
        )

    def list(self) -> List[Parameter]:
        """Return a list of all ``Parameter``'s in the collection."""
        return list(self._parameters.values())


def create_parameter(
    signature_field: "SignatureField",
    parameter_name: str,
    path_parameters: Tuple["PathParameterDefinition", ...],
    generate_examples: bool,
) -> Parameter:
    """Create an OpenAPI Parameter instance."""
    schema = None
    kwargs_model = signature_field.kwarg_model if isinstance(signature_field.kwarg_model, ParameterKwarg) else None

    if any(path_param.name == parameter_name for path_param in path_parameters):
        param_in = ParamType.PATH
        is_required = True
        path_parameter = [p for p in path_parameters if parameter_name in p.name][0]
        schema = create_path_parameter_schema(
            path_parameter=path_parameter,
            field=signature_field,
            generate_examples=generate_examples,
        )

    elif kwargs_model and kwargs_model.header:
        parameter_name = kwargs_model.header
        param_in = ParamType.HEADER
        is_required = signature_field.is_required
    elif kwargs_model and kwargs_model.cookie:
        parameter_name = kwargs_model.cookie
        param_in = ParamType.COOKIE
        is_required = signature_field.is_required
    else:
        is_required = signature_field.is_required
        param_in = ParamType.QUERY
        parameter_name = kwargs_model.query if kwargs_model and kwargs_model.query else parameter_name

    if not schema:
        schema = create_schema(field=signature_field, generate_examples=generate_examples, plugins=[])

    return Parameter(
        name=parameter_name,
        param_in=param_in,
        required=is_required,
        param_schema=schema,
        description=schema.description,
    )


def get_recursive_handler_parameters(
    field_name: str,
    signature_field: "SignatureField",
    dependencies: "Dependencies",
    route_handler: "BaseRouteHandler",
    path_parameters: Tuple["PathParameterDefinition", ...],
    generate_examples: bool,
) -> List[Parameter]:
    """Create and return parameters for a handler.

    If the provided field is not a dependency, a normal parameter is created and returned as a list, otherwise
    `create_parameter_for_handler()` is called to generate parameters for the dependency.
    """

    if field_name not in dependencies:
        return [
            create_parameter(
                signature_field=signature_field,
                parameter_name=field_name,
                path_parameters=path_parameters,
                generate_examples=generate_examples,
            )
        ]
    dependency_fields = dependencies[field_name].signature_model.fields()
    return create_parameter_for_handler(route_handler, dependency_fields, path_parameters, generate_examples)


def get_layered_parameter(
    field_name: str,
    signature_field: "SignatureField",
    layered_parameters: Dict[str, "SignatureField"],
    path_parameters: Tuple["PathParameterDefinition", ...],
    generate_examples: bool,
) -> Parameter:
    """Create a layered parameter for a given signature model field.

    Layer info is extracted from the provided ``layered_parameters`` dict and set as the field's ``field_info`` attribute.
    """
    layer_field = layered_parameters[field_name]

    field = signature_field if signature_field.is_parameter_field else layer_field
    default_value = signature_field.default_value if not signature_field.is_empty else layer_field.default_value
    field_type = signature_field.field_type if signature_field is not Empty else layer_field.field_type  # type: ignore

    parameter_name = field_name
    if isinstance(field.kwarg_model, ParameterKwarg):
        parameter_name = field.kwarg_model.query or field.kwarg_model.header or field.kwarg_model.cookie or field_name

    return create_parameter(
        signature_field=SignatureField.create(
            default_value=default_value,
            kwarg_model=field.kwarg_model,
            name=field_name,
            field_type=field_type,
            extra=field.extra,
            children=field.children,
        ),
        parameter_name=parameter_name,
        path_parameters=path_parameters,
        generate_examples=generate_examples,
    )


def create_parameter_for_handler(
    route_handler: "BaseRouteHandler",
    handler_fields: Dict[str, "SignatureField"],
    path_parameters: Tuple["PathParameterDefinition", ...],
    generate_examples: bool,
) -> List[Parameter]:
    """Create a list of path/query/header Parameter models for the given PathHandler."""
    parameters = ParameterCollection(route_handler=route_handler)
    dependencies = route_handler.resolve_dependencies()

    layered_parameters = route_handler.resolve_layered_parameters()

    unique_handler_fields = tuple(
        (k, v) for k, v in handler_fields.items() if k not in RESERVED_KWARGS and k not in layered_parameters
    )
    unique_layered_fields = tuple(
        (k, v) for k, v in layered_parameters.items() if k not in RESERVED_KWARGS and k not in handler_fields
    )
    intersection_fields = tuple(
        (k, v) for k, v in handler_fields.items() if k not in RESERVED_KWARGS and k in layered_parameters
    )

    for field_name, signature_field in unique_handler_fields:
        if isinstance(signature_field.kwarg_model, DependencyKwarg) and field_name not in dependencies:
            # never document explicit dependencies
            continue

        for parameter in get_recursive_handler_parameters(
            field_name=field_name,
            signature_field=signature_field,
            dependencies=dependencies,
            route_handler=route_handler,
            path_parameters=path_parameters,
            generate_examples=generate_examples,
        ):
            parameters.add(parameter)

    for field_name, signature_field in unique_layered_fields:
        parameters.add(
            create_parameter(
                signature_field=signature_field,
                parameter_name=field_name,
                path_parameters=path_parameters,
                generate_examples=generate_examples,
            )
        )

    for field_name, signature_field in intersection_fields:
        parameters.add(
            get_layered_parameter(
                field_name=field_name,
                signature_field=signature_field,
                layered_parameters=layered_parameters,
                path_parameters=path_parameters,
                generate_examples=generate_examples,
            )
        )

    return parameters.list()
