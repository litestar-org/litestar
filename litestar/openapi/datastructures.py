from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from litestar.enums import MediaType

if TYPE_CHECKING:
    from litestar.types import DataclassProtocol, TypedDictClass

    try:
        from pydantic import BaseModel
    except ImportError:
        BaseModel = Any  # type: ignore

__all__ = ("ResponseSpec",)


@dataclass
class ResponseSpec:
    """Container type of additional responses."""

    data_container: type[BaseModel] | type[DataclassProtocol] | TypedDictClass
    """A model that describes the content of the response."""
    generate_examples: bool = field(default=True)
    """Generate examples for the response content."""
    description: str = field(default="Additional response")
    """A description of the response."""
    media_type: MediaType = field(default=MediaType.JSON)
    """Response media type."""
