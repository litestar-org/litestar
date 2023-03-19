from __future__ import annotations

from inspect import getmodule
from typing import Any

from typing_extensions import get_args, get_type_hints

from .config import DTOConfig
from .exc import InvalidAnnotation

__all__ = (
    "get_model_type_hints",
    "parse_config_from_annotated",
)


def get_model_type_hints(model_type: type[Any]) -> dict[str, Any]:
    """Retrieve type annotations for ``model_type``.

    Args:
        model_type: Any type-annotated class.

    Returns:
        Type hints for ``model_type`` resolved within the scope of its module.
    """
    model_module = getmodule(model_type)
    localns = vars(model_module) if model_module is not None else {}
    return get_type_hints(model_type, localns=localns)


def parse_config_from_annotated(item: Any) -> tuple[type[Any], DTOConfig]:
    """Extract data type and config instance from ``Annotated`` annotation.

    Args:
        item: ``Annotated`` type hint

    Returns:
        The type and config object extracted from the annotation.
    """
    item, expected_config, *_ = get_args(item)
    if not isinstance(expected_config, DTOConfig):
        raise InvalidAnnotation("Annotation metadata must be an instance of `DTOConfig`.")
    return item, expected_config
