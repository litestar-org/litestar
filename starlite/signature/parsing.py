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
    Union,
    cast,
)

from msgspec import defstruct
from pydantic import create_model
from pydantic.fields import FieldInfo, Undefined
from pydantic_factories import ModelFactory
from typing_extensions import get_args

from starlite.constants import SKIP_VALIDATION_NAMES, UNDEFINED_SENTINELS, RESERVED_KWARGS
from starlite.exceptions import ImproperlyConfiguredException
from starlite.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from starlite.plugins.base import (
    PluginMapping,
    SerializationPluginProtocol,
    get_plugin_for_value,
)
from starlite.signature.models import MsgSpecSignatureModel, PydanticSignatureModel
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
    parameter: ParsedSignatureParameter,
    plugin: SerializationPluginProtocol,
    field_plugin_mappings: Dict[str, PluginMapping],
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


class ParsedSignatureResult(NamedTuple):
    parsed_params: List[ParsedSignatureParameter]
    return_annotation: Any
    field_plugin_mappings: Dict[str, PluginMapping]
    dependency_names: Set[str]
    expected_reserved_kwargs: Set[str]

def parse_fn_signature(
    fn: "AnyCallable", plugins: List["SerializationPluginProtocol"], dependency_name_set: Set[str]
) -> ParsedSignatureResult:
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

    dependency_names: Set[str] = set(key for key in signature.parameters.keys() if key in RESERVED_KWARGS)
    expected_reserved_kwargs: Set[str] = set()
    field_plugin_mappings: Dict[str, PluginMapping] = {}
    parsed_params: List[ParsedSignatureParameter] = []

    for parameter in (
        ParsedSignatureParameter.from_parameter(parameter=parameter, parameter_name=name, fn_name=fn_name)
        for name, parameter in signature.parameters.items()
        if name not in ("self", "cls", *RESERVED_KWARGS)
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

    return ParsedSignatureResult(parsed_params=parsed_params, return_annotation=signature.return_annotation, field_plugin_mappings=field_plugin_mappings, dependency_names=dependency_names, expected_reserved_kwargs=expected_reserved_kwargs)


def create_signature_model(
    fn: "AnyCallable", plugins: List["SerializationPluginProtocol"], dependency_name_set: Set[str]
) -> Union[Type["PydanticSignatureModel"], Type["MsgSpecSignatureModel"]]:
    """Create a model for a callable's signature. The model can than be used to parse and validate before passing it to
    the callable.

    Args:
        fn: A callable.
        plugins: A list of plugins.
        dependency_name_set: A set of dependency names

    Returns:
        A signature model.
    """

    unwrapped_fn = cast("AnyCallable", unwrap_partial(fn))
    fn_name = getattr(fn, "__name__", "anonymous")
    fn_module = getattr(fn, "__module__", None)

    result = parse_fn_signature(
        fn=unwrapped_fn,
        plugins=plugins,
        dependency_name_set=dependency_name_set,
    )

    if any(p.annotation and hasattr(p.annotation, "__get_validators__") for p in result.parsed_params):
        signature_model = create_pydantic_signature_model(
            fn_name=fn_name,
            fn_module=fn_module,
            parsed_params=result.parsed_params,
            return_annotation=result.return_annotation,
            field_plugin_mappings=result.field_plugin_mappings,
            dependency_names={*dependency_name_set, *result.dependency_names},
        )
    else:
        signature_model = create_msgspec_signature_model(
            fn_name=fn_name,
            fn_module=fn_module,
            parsed_params=result.parsed_params,
            return_annotation=result.return_annotation,
            field_plugin_mappings=result.field_plugin_mappings,
            dependency_names={*dependency_name_set, *result.dependency_names},
        )

    signature_model.dependency_name_set = result.dependency_names
    signature_model.expected_reserved_kwargs = result.expected_reserved_kwargs
    signature_model.field_plugin_mappings = result.field_plugin_mappings
    signature_model.populate_signature_fields()
    signature_model.return_annotation = result.return_annotation
    return signature_model


def create_msgspec_signature_model(
    fn_name: str,
    fn_module: Optional[str],
    parsed_params: List[ParsedSignatureParameter],
    return_annotation: Any,
    field_plugin_mappings: Dict[str, "PluginMapping"],
    dependency_names: Set[str],
) -> Type["MsgSpecSignatureModel"]:
    struct_params: List[Union[Tuple[str, Type], Tuple[str, Type, Any]]] = []

    for parameter in parsed_params:
        if parameter.should_skip_validation:
            if isinstance(parameter.default, DependencyKwarg):
                struct_params.append(
                    (
                        parameter.name,
                        Any,
                        parameter.default.default if parameter.default.default is not Empty else None,
                    )
                )
            else:
                struct_params.append(
                    (parameter.name, Any, parameter.default)
                    if parameter.default is not Empty
                    else (parameter.name, Any)
                )
        elif isinstance(parameter.default, (ParameterKwarg, BodyKwarg)):
            if parameter.default.default is not Empty:
                struct_params.append((parameter.name, parameter.annotation, parameter.default.default))
            else:
                struct_params.append((parameter.name, parameter.annotation))
        elif parameter.default_defined:
            struct_params.append((parameter.name, parameter.annotation, parameter.default))
        elif not parameter.optional:
            struct_params.append((parameter.name, parameter.annotation))
        else:
            struct_params.append((parameter.name, parameter.annotation, None))

    return cast(
        "Type[MsgSpecSignatureModel]",
        defstruct(
            f"{fn_name}MsgspecSignatureModel",
            struct_params,
            bases=(MsgSpecSignatureModel,),
            module=fn_module,
            kw_only=True,
        ),
    )


def create_pydantic_signature_model(
    fn_name: str,
    fn_module: Optional[str],
    parsed_params: List[ParsedSignatureParameter],
    return_annotation: Any,
    field_plugin_mappings: Dict[str, "PluginMapping"],
    dependency_names: Set[str],
) -> Type["PydanticSignatureModel"]:
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

    model: Type["PydanticSignatureModel"] = create_model(  # type: ignore
        f"{fn_name}PydanticSignatureModel",
        __base__=PydanticSignatureModel,
        __module__=fn_module or "pydantic.main",
        **field_definitions,
    )
    return model
