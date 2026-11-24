from __future__ import annotations

from typing import Any

from litestar.exceptions import LitestarException
from litestar.exceptions.http_exceptions import ImproperlyConfiguredException

__all__ = ("DTOFactoryException", "DTOTransferTypeError", "InvalidAnnotationException", "MissingDTOError")


class DTOFactoryException(LitestarException):
    """Base DTO exception type."""


class InvalidAnnotationException(DTOFactoryException):
    """Unexpected DTO type argument."""


class DTOTransferTypeError(InvalidAnnotationException):
    """msgspec rejects the model, or the type a DTO transfers for it."""


class MissingDTOError(DTOFactoryException, ImproperlyConfiguredException):
    """Data is annotated with DTOData, but no DTO decodes it."""

    annotation: Any
    """The annotation of the data"""

    def __init__(self, *, handler_name: str, annotation: Any) -> None:
        """Initialize ``MissingDTOError``.

        Args:
            handler_name: The name of the handler function
            annotation: The annotation of the data
        """
        super().__init__(
            f"Handler function {handler_name} has a data parameter that is a subclass of DTOData but no DTO has been "
            "registered for it."
        )
        self.annotation = annotation
