from dataclasses import asdict
from inspect import Parameter, Signature
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
)

from pydantic import create_model
from pydantic.fields import FieldInfo, Undefined
from pydantic_factories import ModelFactory
from typing_extensions import get_args

from starlite.constants import SKIP_VALIDATION_NAMES, UNDEFINED_SENTINELS
from starlite.exceptions import ImproperlyConfiguredException
from starlite.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from starlite.plugins.base import PluginMapping, PluginProtocol, get_plugin_for_value
from starlite.signature.models import PydanticSignatureModel, SignatureModel
from starlite.types import Empty
from starlite.utils import is_optional_union
from starlite.utils.helpers import unwrap_partial

if TYPE_CHECKING:
    from starlite.types import AnyCallable


class ParsedSignatureParameter(NamedTuple):
    """Represents the parameters of a callable for purpose of signature model generation."""

    annotation: Any
    default: Any
    name: str
    optional: bool

    @classmethod
    def from_parameter(cls, fn_name: str, parameter_name: str, parameter: Parameter) -> "ParsedSignatureParameter":
        """Initialize ParsedSignatureParameter.

        Args:
            fn_name: Name of function.
            parameter_name: Name of parameter.
            parameter: inspect.Parameter

        Returns:
            ParsedSignatureParameter.
        """
        if parameter.annotation is Signature.empty:
            raise ImproperlyConfiguredException(
                f"Kwarg {parameter_name} of {fn_name} does not have a type annotation. If it "
                f"should receive any value, use the 'Any' type."
            )

        return ParsedSignatureParameter(
            annotation=parameter.annotation,
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


def get_type_annotation_from_plugin(
    parameter: ParsedSignatureParameter, plugin: PluginProtocol, field_plugin_mappings: Dict[str, PluginMapping]
) -> Any:
    """Use plugin declared for parameter annotation type to generate a pydantic model.

    Args:
        parameter:  ParsedSignatureParameter
        plugin: PluginProtocol
        field_plugin_mappings: A dictionary mapping fields for plugin mappings.

    Returns:
        A pydantic model to be used as a type
    """
    type_args = get_args(parameter.annotation)
    type_value = type_args[0] if type_args else parameter.annotation
    field_plugin_mappings[parameter.name] = PluginMapping(plugin=plugin, model_class=type_value)
    pydantic_model = plugin.to_pydantic_model_class(model_class=type_value, parameter_name=parameter.name)
    return List[pydantic_model] if type_args else pydantic_model  # type:ignore[valid-type]


def parse_fn_signature(
    fn: "AnyCallable", plugins: List["PluginProtocol"], dependency_name_set: Set[str]
) -> Tuple[List[ParsedSignatureParameter], Any, Dict[str, PluginMapping], Set[str]]:
    """Parse a function signature into data used for the generation of a signature model.

    Args:
        fn: A callable.
        plugins: A list of plugins.
        dependency_name_set: A set of dependency names

    Returns:
        A tuple containing the following values for generating a signature model: a mapping of field definitions, the
        callable's return annotation, a mapping of field names to plugins - if any, and an updated dependency name set.
    """

    signature = Signature.from_callable(fn)
    fn_name = getattr(fn, "__name__", "anonymous")

    field_plugin_mappings: Dict[str, PluginMapping] = {}
    parsed_params: List[ParsedSignatureParameter] = []
    dependency_names: Set[str] = set()

    for parameter in (
        ParsedSignatureParameter.from_parameter(parameter=parameter, parameter_name=name, fn_name=fn_name)
        for name, parameter in signature.parameters.items()
        if name not in ("self", "cls")
    ):
        if isinstance(parameter.default, DependencyKwarg) and parameter.name not in dependency_name_set:
            if not parameter.optional and (
                isinstance(parameter.default, DependencyKwarg) and parameter.default.default is Empty
            ):
                raise ImproperlyConfiguredException(
                    f"Explicit dependency '{parameter.name}' for '{fn_name}' has no default value, "
                    f"or provided dependency."
                )
            dependency_names.add(parameter.name)

        annotation = parameter.annotation
        if isinstance(parameter.default, ParameterKwarg) and parameter.default.value_type is not Empty:
            annotation = parameter.default.value_type

        if plugin := get_plugin_for_value(value=annotation, plugins=plugins):
            annotation = get_type_annotation_from_plugin(parameter, plugin, field_plugin_mappings)

        parsed_params.append(
            ParsedSignatureParameter(
                annotation=annotation, default=parameter.default, optional=parameter.optional, name=parameter.name
            )
        )

    return parsed_params, signature.return_annotation, field_plugin_mappings, dependency_names


def create_signature_model(
    fn: "AnyCallable", plugins: List["PluginProtocol"], dependency_name_set: Set[str]
) -> Type[SignatureModel]:
    """Create a model for a callable's signature. The model can than be used to parse and validate before passing it to
    the callable.

    Args:
        fn: A callable.
        plugins: A list of plugins.
        dependency_name_set: A set of dependency names

    Returns:
        A signature model.
    """

    unwrapped_fn = unwrap_partial(fn)
    fn_name = getattr(fn, "__name__", "anonymous")
    fn_module = getattr(fn, "__module__", None)

    parsed_params, return_annotation, field_plugin_mappings, dependency_names = parse_fn_signature(
        fn=unwrapped_fn,
        plugins=plugins,
        dependency_name_set=dependency_name_set,
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
    fn_module: Optional[str],
    parsed_params: List[ParsedSignatureParameter],
    return_annotation: Any,
    field_plugin_mappings: Dict[str, "PluginMapping"],
    dependency_names: Set[str],
) -> Type[PydanticSignatureModel]:
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
    field_definitions: Dict[str, Tuple[Any, Any]] = {}

    for parameter in parsed_params:
        if parameter.should_skip_validation:
            if isinstance(parameter.default, DependencyKwarg):
                field_definitions[parameter.name] = (
                    Any,
                    parameter.default.default if parameter.default.default is not Empty else None,
                )
            else:
                field_definitions[parameter.name] = (Any, ...)
        elif isinstance(parameter.default, (ParameterKwarg, BodyKwarg)):
            field_info = FieldInfo(**asdict(parameter.default), kwargs_model=parameter.default)
            field_info.default = parameter.default.default if parameter.default.default is not Empty else Undefined
            field_definitions[parameter.name] = (parameter.annotation, field_info)
        elif ModelFactory.is_constrained_field(parameter.default):
            field_definitions[parameter.name] = (parameter.default, ...)
        elif parameter.default_defined:
            field_definitions[parameter.name] = (parameter.annotation, parameter.default)
        elif not parameter.optional:
            field_definitions[parameter.name] = (parameter.annotation, ...)
        else:
            field_definitions[parameter.name] = (parameter.annotation, None)

    model: Type[PydanticSignatureModel] = create_model(  # type: ignore
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
