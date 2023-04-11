from __future__ import annotations

from inspect import getmembers, isclass
from typing import TYPE_CHECKING, Any, Literal, cast

from litestar.constants import SKIP_VALIDATION_NAMES
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import DependencyKwarg
from litestar.plugins import PluginMapping, get_plugin_for_value
from litestar.types import AnyCallable, Empty
from litestar.utils.helpers import unwrap_partial
from litestar.utils.predicates import is_attrs_class

try:
    import pydantic

    from litestar._signature.models.pydantic_signature_model import PydanticSignatureModel

    pydantic_types: tuple[Any, ...] = tuple(
        cls for _, cls in getmembers(pydantic.types, isclass) if "pydantic.types" in repr(cls)
    )
except ImportError:  # pragma: no cover
    PydanticSignatureModel = Empty  # type: ignore
    pydantic_types = ()

try:
    from litestar._signature.models.attrs_signature_model import AttrsSignatureModel
except ImportError:
    AttrsSignatureModel = Empty  # type: ignore

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from litestar._signature.models.base import SignatureModel
    from litestar.plugins import SerializationPluginProtocol
    from litestar.utils.signature import ParsedParameter, ParsedSignature

__all__ = (
    "create_signature_model",
    "get_signature_model",
)


SignatureModelType: TypeAlias = "type[SignatureModel]"


def create_signature_model(
    dependency_name_set: set[str],
    fn: AnyCallable,
    plugins: list[SerializationPluginProtocol],
    preferred_validation_backend: Literal["pydantic", "attrs"],
    parsed_signature: ParsedSignature,
) -> type[SignatureModel]:
    """Create a model for a callable's signature. The model can than be used to parse and validate before passing it to
    the callable.

    Args:
        dependency_name_set: A set of dependency names
        fn: A callable.
        plugins: A list of plugins.
        preferred_validation_backend: Validation/Parsing backend to prefer, if installed
        parsed_signature: A parsed signature for the handler/dependency function.

    Returns:
        A signature model.
    """

    unwrapped_fn = cast("AnyCallable", unwrap_partial(fn))
    fn_name = getattr(fn, "__name__", "anonymous")
    fn_module = getattr(fn, "__module__", None)

    if fn_name == "<lambda>":
        fn_name = "anonymous"

    dependency_names = _validate_dependencies(
        dependency_name_set=dependency_name_set, fn=unwrapped_fn, parsed_signature=parsed_signature
    )

    field_plugin_mappings = _create_field_plugin_mappings(parsed_signature, plugins)

    model_class = _get_signature_model_type(
        preferred_validation_backend=preferred_validation_backend,
        parsed_signature=parsed_signature,
        field_plugin_mappings=field_plugin_mappings,
    )

    type_overrides = _create_type_overrides(parsed_signature, field_plugin_mappings)

    return model_class.create(
        fn_name=fn_name,
        fn_module=fn_module,
        parsed_signature=parsed_signature,
        field_plugin_mappings=field_plugin_mappings,
        dependency_names={*dependency_name_set, *dependency_names},
        type_overrides=type_overrides,
    )


def get_signature_model(value: Any) -> type[SignatureModel]:
    """Retrieve and validate the signature model from a provider or handler."""
    try:
        return cast(SignatureModelType, value.signature_model)
    except AttributeError as e:  # pragma: no cover
        raise ImproperlyConfiguredException(f"The 'signature_model' attribute for {value} is not set") from e


def _any_attrs_annotation(parsed_signature: ParsedSignature) -> bool:
    for parameter in parsed_signature.parameters.values():
        parsed_type = parameter.parsed_type
        if any(is_attrs_class(t.annotation) for t in parsed_type.inner_types) or is_attrs_class(parsed_type.annotation):
            return True
    return False


def _any_pydantic_annotation(
    parsed_signature: ParsedSignature, field_plugin_mappings: dict[str, PluginMapping]
) -> bool:
    for parameter in parsed_signature.parameters.values():
        parsed_type = parameter.parsed_type
        if (
            any(_is_pydantic_annotation(t.annotation) for t in parsed_type.inner_types)
            or _is_pydantic_annotation(parsed_type.annotation)
            or field_plugin_mappings.get(parameter.name)
        ):
            return True
    return False


def _create_field_plugin_mappings(
    parsed_signature: ParsedSignature, plugins: list[SerializationPluginProtocol]
) -> dict[str, PluginMapping]:
    field_plugin_mappings = {}
    for parameter in parsed_signature.parameters.values():
        parsed_type = parameter.parsed_type
        if plugin := get_plugin_for_value(parameter.parsed_type.annotation, plugins):
            type_value = parsed_type.inner_types[0].annotation if parsed_type.is_collection else parsed_type.annotation
            field_plugin_mappings[parameter.name] = PluginMapping(plugin=plugin, model_class=type_value)
    return field_plugin_mappings


def _create_type_overrides(
    parsed_signature: ParsedSignature, field_plugin_mappings: dict[str, PluginMapping]
) -> dict[str, type]:
    type_overrides = {}
    for parameter in parsed_signature.parameters.values():
        if plugin_mapping := field_plugin_mappings.get(parameter.name):
            type_overrides[parameter.name] = _get_type_annotation_from_plugin_mapping(parameter, plugin_mapping)
        if _should_skip_validation(parameter):
            type_overrides[parameter.name] = Any
    return type_overrides


def _get_signature_model_type(
    preferred_validation_backend: Literal["pydantic", "attrs"],
    parsed_signature: ParsedSignature,
    field_plugin_mappings: dict[str, PluginMapping],
) -> type[SignatureModel]:
    pydantic_installed = PydanticSignatureModel is not Empty  # type: ignore[comparison-overlap]
    attrs_installed = AttrsSignatureModel is not Empty  # type: ignore[comparison-overlap]
    if (
        pydantic_installed
        and (not attrs_installed or not _any_attrs_annotation(parsed_signature))
        and (
            preferred_validation_backend == "pydantic"
            or _any_pydantic_annotation(parsed_signature, field_plugin_mappings)
        )
    ):
        return cast(SignatureModelType, PydanticSignatureModel)
    return cast(SignatureModelType, AttrsSignatureModel)


def _get_type_annotation_from_plugin_mapping(parameter: ParsedParameter, plugin_mapping: PluginMapping) -> Any:
    """Use plugin declared for parameter annotation type to generate a pydantic model.

    Args:
        parameter:  ParsedSignatureParameter
        plugin_mapping: A PluginMapping

    Returns:
        A pydantic model to be used as a type
    """
    parsed_type = parameter.parsed_type
    pydantic_model = plugin_mapping.plugin.to_data_container_class(
        model_class=plugin_mapping.model_class, parameter_name=parameter.name
    )
    return parsed_type.safe_generic_origin[pydantic_model] if parsed_type.is_collection else pydantic_model


def _is_pydantic_annotation(annotation: Any) -> bool:
    return annotation in pydantic_types or hasattr(annotation, "__get_validators__")


def _should_skip_validation(parameter: ParsedParameter) -> bool:
    """Whether the parameter should skip validation.

    Returns:
        A boolean indicating whether the parameter should be validated.
    """
    return parameter.name in SKIP_VALIDATION_NAMES or (
        isinstance(parameter.default, DependencyKwarg) and parameter.default.skip_validation
    )


def _validate_dependencies(
    dependency_name_set: set[str], fn: AnyCallable, parsed_signature: ParsedSignature
) -> set[str]:
    """Validate dependencies of ``parsed_signature``.

    Args:
        dependency_name_set: A set of dependency names
        fn: A callable.
        parsed_signature: A parsed signature.

    Returns:
        A set of validated dependency names.
    """
    fn_name = getattr(fn, "__name__", "anonymous")

    dependency_names: set[str] = set()

    for parameter in parsed_signature.parameters.values():
        if isinstance(parameter.default, DependencyKwarg) and parameter.name not in dependency_name_set:
            if not parameter.parsed_type.is_optional and (
                isinstance(parameter.default, DependencyKwarg) and parameter.default.default is Empty
            ):
                raise ImproperlyConfiguredException(
                    f"Explicit dependency '{parameter.name}' for '{fn_name}' has no default value, "
                    f"or provided dependency."
                )
            dependency_names.add(parameter.name)
    return dependency_names
