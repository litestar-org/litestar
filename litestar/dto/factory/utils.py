from __future__ import annotations

import typing
from inspect import getmodule
from typing import TYPE_CHECKING, TypeVar

from msgspec import Struct
from typing_extensions import get_type_hints

from litestar.utils.signature import ParsedType
from litestar.utils.typing import unwrap_annotation

from .config import DTOConfig
from .exc import InvalidAnnotation

if TYPE_CHECKING:
    from typing import Any


__all__ = (
    "get_model_type_hints",
    "parse_config_from_annotated",
)

T = TypeVar("T")
StructT = TypeVar("StructT", bound=Struct)


def get_model_type_hints(model_type: type[Any], namespace: dict[str, Any] | None = None) -> dict[str, ParsedType]:
    """Retrieve type annotations for ``model_type``.

    Args:
        model_type: Any type-annotated class.
        namespace: Optional namespace to use for resolving type hints.

    Returns:
        Parsed type hints for ``model_type`` resolved within the scope of its module.
    """
    namespace = namespace or {}
    namespace.update(vars(typing))
    model_module = getmodule(model_type)
    if model_module:
        namespace.update(vars(model_module))
    return {k: ParsedType(v) for k, v in get_type_hints(model_type, localns=namespace).items()}


def parse_config_from_annotated(item: Any) -> tuple[type[Any], DTOConfig]:
    """Extract data type and config instance from ``Annotated`` annotation.

    Args:
        item: ``Annotated`` type hint

    Returns:
        The type and config object extracted from the annotation.
    """
    unwrapped, meta, _ = unwrap_annotation(item)
    if not meta:
        return unwrapped, DTOConfig()
    expected_config = meta[0]
    if not isinstance(expected_config, DTOConfig):
        raise InvalidAnnotation("Annotation metadata must be an instance of `DTOConfig`.")
    return unwrapped, expected_config
