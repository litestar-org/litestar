from __future__ import annotations

import typing
from inspect import getmodule
from typing import TYPE_CHECKING, TypeVar

from msgspec import Struct
from typing_extensions import get_type_hints

from litestar.response import Response
from litestar.types.builtin_types import NoneType
from litestar.typing import ParsedType

from .config import DTOConfig
from .data_structures import DTOData
from .exc import InvalidAnnotation

if TYPE_CHECKING:
    from typing import Any

__all__ = (
    "get_model_type_hints",
    "parse_configs_from_annotation",
    "resolve_model_type",
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


def parse_configs_from_annotation(parsed_type: ParsedType) -> tuple[DTOConfig, ...]:
    """Extract data type and config instances from ``Annotated`` annotation.

    Args:
        parsed_type: A parsed type annotation that represents the annotation used to narrow the DTO type.

    Returns:
        The type and config object extracted from the annotation.
    """
    return tuple(item for item in parsed_type.metadata if isinstance(item, DTOConfig))


def resolve_model_type(parsed_type: ParsedType) -> ParsedType:
    """Resolve the data model type from a parsed type.

    Args:
        parsed_type: A parsed type annotation that represents the annotation used to narrow the DTO type.

    Returns:
        The data model type.
    """
    if parsed_type.is_optional:
        return resolve_model_type(next(t for t in parsed_type.inner_types if not t.is_subclass_of(NoneType)))

    if parsed_type.is_subclass_of((DTOData, Response)):
        return resolve_model_type(parsed_type.inner_types[0])

    if parsed_type.is_collection:
        if len(parsed_type.inner_types) != 1:
            raise InvalidAnnotation("AbstractDTOFactory only supports homogeneous collection types")
        return resolve_model_type(parsed_type.inner_types[0])

    return parsed_type
