from typing import Any, Dict

from pydantic import validator
from pydantic_openapi_schema.v3_1_0 import Header


class ResponseHeader(Header):
    """Container type for a response header."""

    documentation_only: bool = False
    """defines the ResponseHeader instance as for OpenAPI documentation purpose only"""
    value: Any = None
    """value to set for the response header"""

    @validator("value", always=True)
    def validate_value(cls, value: Any, values: Dict[str, Any]) -> Any:  # pylint: disable=no-self-argument
        """Ensures that either value is set or the instance is for
        documentation_only."""
        if values.get("documentation_only") or value is not None:
            return value
        raise ValueError("value must be set if documentation_only is false")
