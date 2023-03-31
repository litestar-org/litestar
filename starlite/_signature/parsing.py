from __future__ import annotations

from dataclasses import asdict, dataclass
from inspect import Parameter, Signature
from typing import TYPE_CHECKING, Any, List, cast

from pydantic import create_model
from pydantic.fields import FieldInfo, Undefined
from pydantic_factories import ModelFactory
from typing_extensions import get_args

from starlite._signature.models import PydanticSignatureModel, SignatureModel
from starlite._signature.utils import get_fn_type_hints
from starlite.constants import SKIP_VALIDATION_NAMES, UNDEFINED_SENTINELS
from starlite.datastructures import ImmutableState
from starlite.dto import AbstractDTOInterface
from starlite.exceptions import ImproperlyConfiguredException
from starlite.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from starlite.plugins import (
    PluginMapping,
    SerializationPluginProtocol,
    get_plugin_for_value,
)
from starlite.types import Empty
from starlite.utils import is_class_and_subclass, is_optional_union
from starlite.utils.helpers import unwrap_partial

__all__ = (
    "ParsedSignatureParameter",
    "create_pydantic_signature_model",
    "create_signature_model",
    "get_type_annotation_from_plugin",
    "parse_fn_signature",
)


if TYPE_CHECKING:
    from starlite.types import AnyCallable


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
        return (
            self.name in SKIP_VALIDATION_NAMES
            or is_class_and_subclass(self.annotation, AbstractDTOInterface)  # type:ignore[type-abstract]
            or (isinstance(self.default, DependencyKwarg) and self.default.skip_validation)
        )


def get_type_annotation_from_plugin(
    parameter: ParsedSignatureParameter,
    plugin: SerializationPluginProtocol,
    field_plugin_mappings: dict[str, PluginMapping],
) -> Any:
    """Use plugin declared for parameter annotation type to generate a pydantic model.

    Args:
        parameter:  ParsedSignatureParameter
        plugin: SerializationPluginProtocol
        field_plugin_mappings: A dictionary mapping fields for plugin mappings.

    Returns:
        A pydantic model to be used as a type
    """
    type_args = get_args(parameter.annotation)
    type_value = type_args[0] if type_args else parameter.annotation
    field_plugin_mappings[parameter.name] = PluginMapping(plugin=plugin, model_class=type_value)
    pydantic_model = plugin.to_data_container_class(model_class=type_value, parameter_name=parameter.name)
    return List[pydantic_model] if type_args else pydantic_model  # type:ignore[valid-type]


def parse_fn_signature(
    fn: AnyCallable,
    plugins: list[SerializationPluginProtocol],
    dependency_name_set: set[str],
    signature_namespace: dict[str, Any],
) -> tuple[list[ParsedSignatureParameter], Any, dict[str, PluginMapping], set[str]]:
    """Parse a function signature into data used for the generation of a signature model.

    Args:
        fn: A callable.
        plugins: A list of plugins.
        dependency_name_set: A set of dependency names
        signature_namespace: mapping of names to types for forward reference resolution

    Returns:
        A tuple containing the following values for generating a signature model: a mapping of field definitions, the
        callable's return annotation, a mapping of field names to plugins - if any, and an updated dependency name set.
    """
    signature = Signature.from_callable(fn)
    fn_name = getattr(fn, "__name__", "anonymous")

    field_plugin_mappings: dict[str, PluginMapping] = {}
    parsed_params: list[ParsedSignatureParameter] = []
    dependency_names: set[str] = set()
    fn_type_hints = get_fn_type_hints(fn, namespace=signature_namespace)

    parameters = (
        ParsedSignatureParameter.from_parameter(
            parameter=parameter, parameter_name=name, fn_name=fn_name, fn_type_hints=fn_type_hints
        )
        for name, parameter in signature.parameters.items()
        if name not in ("self", "cls")
    )
    for parameter in parameters:
        if parameter.name == "state" and not issubclass(parameter.annotation, ImmutableState):
            raise ImproperlyConfiguredException(
                f"The type annotation `{parameter.annotation}` is an invalid type for the 'state' reserved kwarg. "
                "It must be typed to a subclass of `starlite.datastructures.ImmutableState` or "
                "`starlite.datastructures.State`."
            )

        if isinstance(parameter.default, DependencyKwarg) and parameter.name not in dependency_name_set:
            if not parameter.optional and (
                isinstance(parameter.default, DependencyKwarg) and parameter.default.default is Empty
            ):
                raise ImproperlyConfiguredException(
                    f"Explicit dependency '{parameter.name}' for '{fn_name}' has no default value, "
                    f"or provided dependency."
                )
            dependency_names.add(parameter.name)

        if isinstance(parameter.default, ParameterKwarg) and parameter.default.value_type is not Empty:
            parameter.annotation = parameter.default.value_type

        if plugin := get_plugin_for_value(value=parameter.annotation, plugins=plugins):
            parameter.annotation = get_type_annotation_from_plugin(parameter, plugin, field_plugin_mappings)

        parsed_params.append(parameter)

    return parsed_params, fn_type_hints.get("return", Signature.empty), field_plugin_mappings, dependency_names


def create_signature_model(
    fn: AnyCallable,
    plugins: list[SerializationPluginProtocol],
    dependency_name_set: set[str],
    signature_namespace: dict[str, Any],
) -> type[SignatureModel]:
    """Create a model for a callable's signature. The model can than be used to parse and validate before passing it to
    the callable.

    Args:
        fn: A callable.
        plugins: A list of plugins.
        dependency_name_set: A set of dependency names
        signature_namespace: mapping of names to types for forward reference resolution

    Returns:
        A _signature model.
    """
    unwrapped_fn = cast("AnyCallable", unwrap_partial(fn))
    fn_name = getattr(fn, "__name__", "anonymous")
    fn_module = getattr(fn, "__module__", None)

    parsed_params, return_annotation, field_plugin_mappings, dependency_names = parse_fn_signature(
        fn=unwrapped_fn,
        plugins=plugins,
        dependency_name_set=dependency_name_set,
        signature_namespace=signature_namespace,
    )

    # TODO: we will implement logic here to determine what kind of SignatureModel we are creating.
    # For now this is only pydantic:

    return create_pydantic_signature_model(
        fn_name=fn_name,
        fn_module=fn_module,
        parsed_params=parsed_params,
        return_annotation=return_annotation,
        field_plugin_mappings=field_plugin_mappings,
        dependency_names={*dependency_name_set, *dependency_names},
    )


def create_pydantic_signature_model(
    fn_name: str,
    fn_module: str | None,
    parsed_params: list[ParsedSignatureParameter],
    return_annotation: Any,
    field_plugin_mappings: dict[str, PluginMapping],
    dependency_names: set[str],
) -> type[PydanticSignatureModel]:
    """Create a pydantic based SignatureModel.

    Args:
        fn_name: Name of the callable.
        fn_module: Name of the function's module, if any.
        parsed_params: A list of parsed signature parameters.
        return_annotation: Annotation for the callable's return value.
        field_plugin_mappings: A mapping of field names to plugin mappings.
        dependency_names: A set of dependency names.

    Returns:
        The created PydanticSignatureModel.
    """
    field_definitions: dict[str, tuple[Any, Any]] = {}

    for parameter in parsed_params:
        if isinstance(parameter.default, (ParameterKwarg, BodyKwarg)):
            field_info = FieldInfo(
                **asdict(parameter.default), kwargs_model=parameter.default, parsed_parameter=parameter
            )
        else:
            field_info = FieldInfo(default=..., parsed_parameter=parameter)
        if parameter.should_skip_validation:
            field_type = Any
            if isinstance(parameter.default, DependencyKwarg):
                field_info.default = parameter.default.default if parameter.default.default is not Empty else None
        elif isinstance(parameter.default, (ParameterKwarg, BodyKwarg)):
            field_type = parameter.annotation
            field_info.default = parameter.default.default if parameter.default.default is not Empty else Undefined
        elif ModelFactory.is_constrained_field(parameter.default):
            field_type = parameter.default
        elif parameter.default_defined:
            field_type = parameter.annotation
            field_info.default = parameter.default
        elif not parameter.optional:
            field_type = parameter.annotation
        else:
            field_type = parameter.annotation
            field_info.default = None

        field_definitions[parameter.name] = (field_type, field_info)

    model: type[PydanticSignatureModel] = create_model(  # type: ignore
        f"{fn_name}_signature_model",
        __base__=PydanticSignatureModel,
        __module__=fn_module or "pydantic.main",
        **field_definitions,
    )
    model.return_annotation = return_annotation
    model.field_plugin_mappings = field_plugin_mappings
    model.dependency_name_set = dependency_names
    model.populate_signature_fields()
    return model
