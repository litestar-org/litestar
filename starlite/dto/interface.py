from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from typing_extensions import Self

    from starlite.connection import Request
    from starlite.handlers import BaseRouteHandler
    from starlite.types import StarliteEncodableType
    from starlite.types.parsed_signature import ParsedType

__all__ = ("DTOInterface",)


@runtime_checkable
class DTOInterface(Protocol):
    __slots__ = ()

    @abstractmethod
    def to_data_type(self) -> Any:
        """Return the data held by the DTO."""

    @abstractmethod
    def to_encodable_type(self, request: Request[Any, Any, Any]) -> bytes | StarliteEncodableType:
        """Encode data held by the DTO type to a type supported by starlite serialization.

        Can return either bytes or a type that Starlite can return to bytes.

        Args:
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
            DTOInterface instance.
        """

    @classmethod
    @abstractmethod
    def from_data(cls, data: Any) -> Self:
        """Construct an instance from data.

        Args:
            data: Data to construct the DTO from.

        Returns:
            DTOInterface instance.
        """

    @classmethod
    def on_registration(cls, parsed_type: ParsedType, route_handler: BaseRouteHandler) -> None:
        """Do something each time the DTOInterface type is encountered during signature modelling.

        Args:
            parsed_type: :class:`ParsedType <.types.parsed_signature.ParsedType>` instance, will be either the parsed
                annotation of a ``"data"`` kwarg, or the parsed return type annotation of a route handler.
            route_handler: :class:`HTTPRouteHandler <.handlers.HTTPRouteHandler>` DTO type is declared upon.
        """
