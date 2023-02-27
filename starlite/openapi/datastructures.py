from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from starlite.enums import MediaType

if TYPE_CHECKING:
    from pydantic import BaseModel


@dataclass
class ResponseSpec:
    """Container type of additional responses."""

    model: type[BaseModel]
    """A model that describes the content of the response."""
    generate_examples: bool = field(default=True)
    """Generate examples for the response content."""
    description: str = field(default="Additional response")
    """A description of the response."""
    media_type: MediaType = field(default=MediaType.JSON)
    """Response media type."""
