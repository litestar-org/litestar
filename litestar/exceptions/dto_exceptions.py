from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from litestar.exceptions import LitestarException
from litestar.exceptions.http_exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from litestar.dto.base_dto import AbstractDTO

__all__ = (
    "DTOFactoryException",
    "DTONotApplicableError",
    "DTOTransferTypeError",
    "InvalidAnnotationException",
    "MissingDTOError",
)


class DTOFactoryException(LitestarException):
    """Base DTO exception type."""


class InvalidAnnotationException(DTOFactoryException):
    """Unexpected DTO type argument."""


class DTONotApplicableError(InvalidAnnotationException):
    """A DTO declared on a route handler cannot handle the annotation it is declared for."""

    dto: type[AbstractDTO[Any]]
    """The declared DTO"""
    option: Literal["dto", "return_dto"]
    """The option the DTO is declared with"""
    annotation: Any
    """The annotation the DTO cannot handle"""

    def __init__(
        self,
        message: str,
        *,
        dto: type[AbstractDTO[Any]],
        option: Literal["dto", "return_dto"],
        annotation: Any,
    ) -> None:
        """Initialize ``DTONotApplicableError``.

        Args:
            message: The error message
            dto: The declared DTO
            option: The option the DTO is declared with
            annotation: The annotation the DTO cannot handle
        """
        super().__init__(message)
        self.dto = dto
        self.option = option
        self.annotation = annotation


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
