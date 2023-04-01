from __future__ import annotations

from inspect import getmembers, isclass
from typing import TYPE_CHECKING, Any, Literal, cast

from litestar._signature.parsing.utils import parse_fn_signature
from litestar.exceptions import ImproperlyConfiguredException
from litestar.types import AnyCallable, Empty
from litestar.utils.helpers import unwrap_partial
from litestar.utils.predicates import is_attrs_class

try:
    import pydantic

    from litestar._signature.models.pydantic_signature_model import PydanticSignatureModel

    pydantic_types: tuple[Any, ...] = tuple(
        cls for _, cls in getmembers(pydantic.types, isclass) if "pydantic.types" in repr(cls)
    )
except ImportError:
    PydanticSignatureModel = Empty  # type: ignore
    pydantic_types = ()

try:
    from litestar._signature.models.attrs_signature_model import AttrsSignatureModel
except ImportError:
    AttrsSignatureModel = Empty  # type: ignore

if TYPE_CHECKING:
    from litestar._signature.models.base import SignatureModel
    from litestar._signature.parsing import ParsedSignatureParameter
    from litestar.plugins import SerializationPluginProtocol


__all__ = ("create_signature_model", "get_signature_model")


def _get_signature_model(
    preferred_validation_backend: Literal["pydantic", "attrs"], parsed_params: list[ParsedSignatureParameter]
) -> SignatureModel:
    pydantic_installed = PydanticSignatureModel is not Empty  # type: ignore[comparison-overlap]
    attrs_installed = AttrsSignatureModel is not Empty  # type: ignore[comparison-overlap]

    if (
        pydantic_installed
        and (not attrs_installed or not any(is_attrs_class(p.annotation) for p in parsed_params))
        and (
            preferred_validation_backend == "pydantic"
            or any(p.annotation in pydantic_types or hasattr(p.annotation, "__get_validators__") for p in parsed_params)
        )
    ):
        return cast("SignatureModel", PydanticSignatureModel)
    return cast("SignatureModel", AttrsSignatureModel)


def get_signature_model(value: Any) -> type[SignatureModel]:
    """Retrieve and validate the signature model from a provider or handler."""
    try:
        return cast("type[SignatureModel]", value.signature_model)
    except AttributeError as e:  # pragma: no cover
        raise ImproperlyConfiguredException(f"The 'signature_model' attribute for {value} is not set") from e


def create_signature_model(
    dependency_name_set: set[str],
    fn: AnyCallable,
    plugins: list[SerializationPluginProtocol],
    preferred_validation_backend: Literal["pydantic", "attrs"],
    signature_namespace: dict[str, Any],
) -> type[SignatureModel]:
    """Create a model for a callable's signature. The model can than be used to parse and validate before passing it to
    the callable.

    Args:
        dependency_name_set: A set of dependency names
        fn: A callable.
        plugins: A list of plugins.
        preferred_validation_backend: Validation/Parsing backend to prefer, if installed
        signature_namespace: mapping of names to types for forward reference resolution

    Returns:
        A signature model.
    """

    unwrapped_fn = cast("AnyCallable", unwrap_partial(fn))
    fn_name = getattr(fn, "__name__", "anonymous")
    fn_module = getattr(fn, "__module__", None)

    if fn_name == "<lambda>":
        fn_name = "anonymous"

    parsed_params, return_annotation, field_plugin_mappings, dependency_names = parse_fn_signature(
        dependency_name_set=dependency_name_set,
        fn=unwrapped_fn,
        plugins=plugins,
        signature_namespace=signature_namespace,
    )

    model_class = _get_signature_model(
        preferred_validation_backend=preferred_validation_backend, parsed_params=parsed_params
    )

    return model_class.create(
        fn_name=fn_name,
        fn_module=fn_module,
        parsed_params=parsed_params,
        return_annotation=return_annotation,
        field_plugin_mappings=field_plugin_mappings,
        dependency_names={*dependency_name_set, *dependency_names},
    )
