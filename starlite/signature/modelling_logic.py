from inspect import Signature
from typing import TYPE_CHECKING, Any, Dict, List, Set, Tuple, Type

from pydantic import create_model
from pydantic.fields import FieldInfo, Undefined
from pydantic_factories import ModelFactory
from typing_extensions import get_args

from starlite.exceptions import ImproperlyConfiguredException
from starlite.plugins.base import PluginMapping, PluginProtocol, get_plugin_for_value
from starlite.signature.models import PydanticSignatureModel, SignatureModel
from starlite.signature.parameter import SignatureParameter
from starlite.utils import is_dependency_field
from starlite.utils.helpers import unwrap_partial

if TYPE_CHECKING:
    from starlite.types import AnyCallable


def get_type_annotation_from_plugin(
    parameter: SignatureParameter, plugin: PluginProtocol, field_plugin_mappings: Dict[str, PluginMapping]
) -> Any:
    """Use plugin declared for parameter annotation type to generate a pydantic model.

    Args:
        parameter:  SignatureParameter
        plugin: PluginProtocol

    Returns:
        A pydantic model to be used as a type
    """
    type_args = get_args(parameter.annotation)
    type_value = type_args[0] if type_args else parameter.annotation
    field_plugin_mappings[parameter.name] = PluginMapping(plugin=plugin, model_class=type_value)
    pydantic_model = plugin.to_pydantic_model_class(model_class=type_value, parameter_name=parameter.name)
    if type_args:
        return List[pydantic_model]  # type:ignore[valid-type]
    return pydantic_model


def create_field_definition_from_parameter(parameter: SignatureParameter) -> Tuple[Any, Any]:
    """Construct an `(<annotation>, <default>)` tuple, appropriate for `pydantic.create_model()`.

    Args:
        parameter: SignatureParameter

    Returns:
        tuple[Any, Any]
    """
    if parameter.should_skip_validation:
        if is_dependency_field(parameter.default):
            return Any, parameter.default.default
        return Any, ...

    if ModelFactory.is_constrained_field(parameter.default):
        return parameter.default, ...

    if parameter.default_defined:
        return parameter.annotation, parameter.default

    if not parameter.optional:
        return parameter.annotation, ...

    return parameter.annotation, None


def parse_fn_signature(
    fn: "AnyCallable", plugins: List["PluginProtocol"], dependency_name_set: Set[str]
) -> Tuple[Dict[str, Any], Any, Dict[str, PluginMapping], Set[str]]:
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
    field_definitions: Dict[str, Any] = {}
    dependency_names: Set[str] = set()
    for parameter in (
        SignatureParameter(fn_name, param_name, param_def)
        for param_name, param_def in signature.parameters.items()
        if param_name not in ("self", "cls")
    ):
        if is_dependency_field(parameter.default) and parameter.name not in dependency_name_set:
            if not parameter.optional and (
                isinstance(parameter.default, FieldInfo) and parameter.default.default is Undefined
            ):
                raise ImproperlyConfiguredException(
                    f"Explicit dependency '{parameter.name}' for '{fn_name}' has no default value, "
                    f"or provided dependency."
                )
            dependency_names.add(parameter.name)

        if plugin := get_plugin_for_value(value=parameter.annotation, plugins=plugins):
            parameter.annotation = get_type_annotation_from_plugin(parameter, plugin, field_plugin_mappings)

        field_definitions[parameter.name] = create_field_definition_from_parameter(parameter)

    return field_definitions, signature.return_annotation, field_plugin_mappings, dependency_names


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

    field_definitions, return_annotation, field_plugin_mappings, dependency_names = parse_fn_signature(
        fn=unwrapped_fn,
        plugins=plugins,
        dependency_name_set=dependency_name_set,
    )

    model: Type[SignatureModel] = create_model(
        f"{fn_name}_signature_model",
        __base__=PydanticSignatureModel,
        __module__=fn_module or "pydantic.main",
        **field_definitions,
    )
    model.return_annotation = return_annotation
    model.field_plugin_mappings = field_plugin_mappings
    model.dependency_name_set = {*dependency_name_set, *dependency_names}
    return model
