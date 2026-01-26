from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.schema_generation.utils import get_formatted_examples
from litestar.constants import RESERVED_KWARGS
from litestar.enums import ParamType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec.parameter import Parameter
from litestar.openapi.spec.schema import Schema
from litestar.params import DependencyKwarg, ParameterKwarg
from litestar.types import Empty
from litestar.typing import FieldDefinition
from litestar.utils.predicates import is_optional_union

if TYPE_CHECKING:
    from litestar._openapi.datastructures import OpenAPIContext
    from litestar.handlers.base import BaseRouteHandler
    from litestar.openapi.spec import Reference
    from litestar.types.internal_types import PathParameterDefinition

__all__ = ("create_parameters_for_handler",)

_DOCUMENTABLE_RESERVED_KWARGS: dict[str, ParamType] = {
    "query": ParamType.QUERY,
    "headers": ParamType.HEADER,
    "cookies": ParamType.COOKIE,
}


def _is_struct_type(annotation: Any) -> bool:
    """Check if the annotation is a msgspec Struct type."""
    try:
        from msgspec import Struct

        return isinstance(annotation, type) and issubclass(annotation, Struct)
    except ImportError:
        return False


def _is_attrs_type(annotation: Any) -> bool:
    """Check if the annotation is an attrs class."""
    try:
        import attrs

        return isinstance(annotation, type) and attrs.has(annotation)
    except (ImportError, TypeError):
        return False


class ParameterCollection:
    """Facilitates conditional deduplication of parameters.

    If multiple parameters with the same name are produced for a handler, the condition is ignored if the two
    ``Parameter`` instances are the same (the first is retained and any duplicates are ignored). If the ``Parameter``
    instances are not the same, an exception is raised.
    """

    def __init__(self, route_handler: BaseRouteHandler) -> None:
        """Initialize ``ParameterCollection``.

        Args:
            route_handler: Associated route handler
        """
        self.route_handler = route_handler
        self._parameters: dict[tuple[str, str], Parameter] = {}

    def add(self, parameter: Parameter) -> None:
        """Add a ``Parameter`` to the collection.

        If an existing parameter with the same name and type already exists, the
        parameter is ignored.

        If an existing parameter with the same name but different type exists, raises
        ``ImproperlyConfiguredException``.
        """

        if (parameter.name, parameter.param_in) not in self._parameters:
            # because we are defining routes as unique per path, we have to handle here a situation when there is an optional
            # path parameter. e.g. get(path=["/", "/{param:str}"]). When parsing the parameter for path, the route handler
            # would still have a kwarg called param:
            # def handler(param: str | None) -> ...
            if parameter.param_in != ParamType.QUERY or all(
                f"{{{parameter.name}:" not in path for path in self.route_handler.paths
            ):
                self._parameters[(parameter.name, parameter.param_in)] = parameter
            return

        pre_existing = self._parameters[(parameter.name, parameter.param_in)]
        if parameter == pre_existing:
            return

        raise ImproperlyConfiguredException(
            f"OpenAPI schema generation for handler `{self.route_handler}` detected multiple parameters named "
            f"'{parameter.name}' with different types."
        )

    def list(self) -> list[Parameter]:
        """Return a list of all ``Parameter``'s in the collection."""
        return list(self._parameters.values())


class ParameterFactory:
    """Factory for creating OpenAPI Parameters for a given route handler."""

    def __init__(
        self,
        context: OpenAPIContext,
        route_handler: BaseRouteHandler,
        path_parameters: dict[str, PathParameterDefinition],
    ) -> None:
        """Initialize ParameterFactory.

        Args:
            context: The OpenAPI context.
            route_handler: The route handler.
            path_parameters: The path parameters for the route.
        """
        self.context = context
        self.schema_creator = SchemaCreator.from_openapi_context(self.context, prefer_alias=True)
        self.route_handler = route_handler
        self.parameters = ParameterCollection(route_handler)
        self.dependency_providers = route_handler.dependencies
        self.layered_parameters = route_handler.parameter_field_definitions
        self.path_parameters = path_parameters

    def create_parameter(self, field_definition: FieldDefinition, parameter_name: str) -> Parameter:
        """Create an OpenAPI Parameter instance for a field definition.

        Args:
            field_definition: The field definition.
            parameter_name: The name of the parameter.
        """

        result: Schema | Reference | None = None
        kwarg_definition = (
            field_definition.kwarg_definition if isinstance(field_definition.kwarg_definition, ParameterKwarg) else None
        )

        if parameter_name in self.path_parameters:
            param_in = ParamType.PATH
            is_required = True
            result = self.schema_creator.for_field_definition(field_definition)
        elif kwarg_definition and kwarg_definition.header:
            parameter_name = kwarg_definition.header
            param_in = ParamType.HEADER
            is_required = field_definition.is_required
        elif kwarg_definition and kwarg_definition.cookie:
            parameter_name = kwarg_definition.cookie
            param_in = ParamType.COOKIE
            is_required = field_definition.is_required
        else:
            is_required = field_definition.is_required
            param_in = ParamType.QUERY
            parameter_name = kwarg_definition.query if kwarg_definition and kwarg_definition.query else parameter_name

        if not result:
            result = self.schema_creator.for_field_definition(field_definition)

        schema = result if isinstance(result, Schema) else self.context.schema_registry.from_reference(result).schema

        examples_list = kwarg_definition.examples or [] if kwarg_definition else []
        examples = get_formatted_examples(field_definition, examples_list)

        return Parameter(
            description=schema.description,
            name=parameter_name,
            param_in=param_in,
            required=is_required,
            schema=result,
            examples=examples or None,
        )

    def get_layered_parameter(self, field_name: str, field_definition: FieldDefinition) -> Parameter:
        """Create a parameter for a field definition that has a KwargDefinition defined on the layers.

        Args:
            field_name: The name of the field.
            field_definition: The field definition.
        """
        layer_field = self.layered_parameters[field_name]

        field = field_definition if field_definition.is_parameter_field else layer_field
        default = layer_field.default if field_definition.has_default else field_definition.default
        annotation = field_definition.annotation if field_definition is not Empty else layer_field.annotation

        parameter_name = field_name
        if isinstance(field.kwarg_definition, ParameterKwarg):
            parameter_name = (
                field.kwarg_definition.query
                or field.kwarg_definition.header
                or field.kwarg_definition.cookie
                or field_name
            )

        field_definition = FieldDefinition.from_kwarg(
            inner_types=field.inner_types,
            default=default,
            extra=field.extra,
            annotation=annotation,
            kwarg_definition=field.kwarg_definition,
            name=field_name,
        )
        return self.create_parameter(field_definition=field_definition, parameter_name=parameter_name)

    def _is_model_field_definition(self, field_definition: FieldDefinition) -> bool:
        """Check if a FieldDefinition represents a decomposable model type.

        Args:
            field_definition: The field definition to inspect.
        """
        if field_definition.is_dataclass_type or field_definition.is_typeddict_type:
            return True
        return self.schema_creator.get_plugin_for(field_definition) is not None

    @staticmethod
    def _get_model_required_fields(field_definition: FieldDefinition, type_hints: dict[str, Any]) -> set[str]:
        """Determine which fields in a model type are required.

        Args:
            field_definition: The model's field definition.
            type_hints: Resolved type hints mapping field names to their annotations.
        """
        model_type = field_definition.type_

        if field_definition.is_dataclass_type:
            required: set[str] = set()
            for dc_field in dataclasses.fields(model_type):
                if (
                    dc_field.default is dataclasses.MISSING
                    and dc_field.default_factory is dataclasses.MISSING
                    and not is_optional_union(type_hints[dc_field.name])
                ):
                    required.add(dc_field.name)
            return required

        if field_definition.is_typeddict_type:
            required_keys: set[str] = getattr(model_type, "__required_keys__", set())
            return {k for k in required_keys if not is_optional_union(type_hints[k])}

        # Generic approach for plugin-supported types (Pydantic, msgspec, attrs, etc.)
        required = {name for name, hint in type_hints.items() if not is_optional_union(hint)}

        # Refine using model-specific default detection
        if hasattr(model_type, "model_fields"):
            # Pydantic v2
            for name, field_info in model_type.model_fields.items():
                if not field_info.is_required():
                    required.discard(name)
        elif _is_struct_type(model_type):
            import msgspec.inspect

            for f in msgspec.inspect.type_info(model_type).fields:
                if not f.required:
                    required.discard(f.name)
        elif _is_attrs_type(model_type):
            import attrs

            for f in attrs.fields(model_type):
                if f.default is not attrs.NOTHING:
                    required.discard(f.name)

        return required

    def _create_parameters_from_model(self, field_definition: FieldDefinition, param_type: ParamType) -> None:
        """Decompose a model-typed reserved kwarg into individual OpenAPI parameters.

        Args:
            field_definition: The model's field definition.
            param_type: The OpenAPI parameter location (query, header, or cookie).
        """
        type_hints = field_definition.get_type_hints(include_extras=True, resolve_generics=True)
        required_fields = self._get_model_required_fields(field_definition, type_hints)

        for field_name, field_type in type_hints.items():
            fd = FieldDefinition.from_kwarg(
                annotation=field_type,
                name=field_name,
            )

            result = self.schema_creator.for_field_definition(fd)
            schema = result if isinstance(result, Schema) else self.context.schema_registry.from_reference(result).schema

            self.parameters.add(
                Parameter(
                    name=field_name,
                    param_in=param_type,
                    required=field_name in required_fields,
                    schema=result,
                    description=schema.description,
                )
            )

    def create_parameters_for_field_definitions(self, fields: dict[str, FieldDefinition]) -> None:
        """Add Parameter models to the handler's collection for the given field definitions.

        Args:
            fields: The field definitions.
        """
        unique_handler_fields = (
            (k, v) for k, v in fields.items() if k not in RESERVED_KWARGS and k not in self.layered_parameters
        )
        unique_layered_fields = (
            (k, v) for k, v in self.layered_parameters.items() if k not in RESERVED_KWARGS and k not in fields
        )
        intersection_fields = (
            (k, v) for k, v in fields.items() if k not in RESERVED_KWARGS and k in self.layered_parameters
        )

        for field_name, field_definition in unique_handler_fields:
            kwarg_definition = field_definition.kwarg_definition
            if isinstance(kwarg_definition, DependencyKwarg) and field_name not in self.dependency_providers:
                # never document explicit dependencies
                continue

            if isinstance(kwarg_definition, ParameterKwarg) and not kwarg_definition.include_in_schema:
                # exclude parameters that are marked as not included in the schema
                continue

            if provider := self.dependency_providers.get(field_name):
                self.create_parameters_for_field_definitions(fields=provider.parsed_fn_signature.parameters)
            else:
                self.parameters.add(self.create_parameter(field_definition=field_definition, parameter_name=field_name))

        for field_name, field_definition in unique_layered_fields:
            self.parameters.add(self.create_parameter(field_definition=field_definition, parameter_name=field_name))

        for field_name, field_definition in intersection_fields:
            self.parameters.add(self.get_layered_parameter(field_name=field_name, field_definition=field_definition))

        # Handle model-typed reserved kwargs (e.g., query: SomeModel, headers: SomeModel)
        # by decomposing the model's fields into individual OpenAPI parameters.
        for kwarg_name, param_type in _DOCUMENTABLE_RESERVED_KWARGS.items():
            if kwarg_name in fields:
                field_def = fields[kwarg_name]
                if self._is_model_field_definition(field_def):
                    self._create_parameters_from_model(field_def, param_type)

    def create_parameters_for_handler(self) -> list[Parameter]:
        """Create a list of path/query/header Parameter models for the given PathHandler."""
        handler_fields = self.route_handler.parsed_fn_signature.parameters
        # not all path parameters have to be consumed by the handler. Because even not
        # consumed path parameters must still be specified, we create stub parameters
        # for the unconsumed ones so a correct OpenAPI schema can be generated
        dependency_fields = {
            name for dep in self.dependency_providers.values() for name in dep.parsed_fn_signature.parameters
        }
        params_not_consumed_by_handler = set(self.path_parameters) - handler_fields.keys()
        unconsumed_path_parameters = params_not_consumed_by_handler - dependency_fields
        handler_fields.update(
            {
                param_name: FieldDefinition.from_kwarg(self.path_parameters[param_name].type, name=param_name)
                for param_name in unconsumed_path_parameters
            }
        )

        self.create_parameters_for_field_definitions(handler_fields)
        return self.parameters.list()


def create_parameters_for_handler(
    context: OpenAPIContext,
    route_handler: BaseRouteHandler,
    path_parameters: dict[str, PathParameterDefinition],
) -> list[Parameter]:
    """Create a list of path/query/header Parameter models for the given PathHandler."""
    factory = ParameterFactory(
        context=context,
        route_handler=route_handler,
        path_parameters=path_parameters,
    )
    return factory.create_parameters_for_handler()
