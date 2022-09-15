from typing import Type

from pydantic import BaseModel

from starlite.enums import MediaType


class ResponseSpec(BaseModel):
    """Container type of additional responses."""

    model: Type[BaseModel]
    """A model that describes the content of the response"""
    generate_examples: bool = True
    """Generate examples for the response content"""
    description: str = "Additional response"
    """A description of the response"""
    media_type: MediaType = MediaType.JSON
    """Response media type"""
