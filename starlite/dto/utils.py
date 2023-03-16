from __future__ import annotations

from typing import Any

from typing_extensions import get_args

from .config import DTOConfig
from .exc import InvalidAnnotation

__all__ = ("parse_config_from_annotated",)


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
