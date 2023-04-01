from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from typing import TypeAlias

    from typing_extensions import Self

    from starlite.connection import Request
    from starlite.enums import MediaType
    from starlite.handlers import BaseRouteHandler

__all__ = (
    "AbstractDTOInterface",
    "DataT",
    "StarliteEncodableType",
)

DataT = TypeVar("DataT")
"""Type var representing data held by a DTO instance."""

StarliteEncodableType: TypeAlias = "Any"
"""Types able to be encoded by Starlite."""


class AbstractDTOInterface(Generic[DataT], metaclass=ABCMeta):
    @abstractmethod
    def to_data_type(self) -> DataT:
        """Return the data held by the DTO."""

    @abstractmethod
    def to_encodable_type(
        self, media_type: str | MediaType, request: Request[Any, Any, Any]
    ) -> bytes | StarliteEncodableType:
        """Encode data held by the DTO type to a type supported by starlite serialization.

        Can return either bytes or a type that Starlite can return to bytes.

        If returning bytes, must respect ``media_type``.

        If media type not supported raise `SerializationException`.

        If returning a ``StarliteEncodableType``, ignore ``media_type``.

        Args:
            media_type: expected encoding type of serialized data
            request: :class:`Request <.connection.Request>` instance.

        Returns:
            Either ``bytes`` or a type that Starlite can convert to bytes.
        """

    @classmethod
    @abstractmethod
    async def from_connection(cls, connection: Request[Any, Any, Any]) -> Self:
        """Construct an instance from a :class:`Request <.connection.Request>`.

        Args:
            connection: :class:`Request <.connection.Request>` instance.

        Returns:
            AbstractDTOInterface instance.
        """

    @classmethod
    @abstractmethod
    def from_data(cls, data: DataT) -> Self:
        """Construct an instance from data.

        Args:
            data: Data to construct the DTO from.

        Returns:
            AbstractDTOInterface instance.
        """

    @classmethod
    def on_startup(cls, resolved_handler_annotation: Any, route_handler: BaseRouteHandler) -> None:
        """Do something each time the AbstractDTOInterface type is encountered during signature modelling.

        Args:
            resolved_handler_annotation: Resolved annotation of the handler function.
            route_handler: :class:`HTTPRouteHandler <.handlers.HTTPRouteHandler>` DTO type is declared upon.
        """
