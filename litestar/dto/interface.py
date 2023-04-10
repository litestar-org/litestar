from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from typing_extensions import Self

    from litestar.connection import Request
    from litestar.handlers import BaseRouteHandler
    from litestar.types import LitestarEncodableType
    from litestar.utils.signature import ParsedType

__all__ = ("DTOInterface",)


@runtime_checkable
class DTOInterface(Protocol):
    __slots__ = ()

    @abstractmethod
    def to_data_type(self) -> Any:
        """Return the data held by the DTO."""

    @abstractmethod
    def to_encodable_type(self, request: Request[Any, Any, Any]) -> bytes | LitestarEncodableType:
        """Encode data held by the DTO type to a type supported by litestar serialization.

        Can return either bytes or a type that Litestar can return to bytes.

        Args:
            request: :class:`Request <.connection.Request>` instance.

        Returns:
            Either ``bytes`` or a type that Litestar can convert to bytes.
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
        """Receive the ``parsed_type`` and ``route_handler`` that this DTO is configured to represent.

        At this point, if the DTO type does not support the annotated type of ``parsed_type``, it should raise an
        ``UnsupportedType`` exception.

        Args:
            parsed_type: ParsedType instance, will be either the parsed
                annotation of a ``"data"`` kwarg, or the parsed return type annotation of a route handler.
            route_handler: :class:`HTTPRouteHandler <.handlers.HTTPRouteHandler>` DTO type is declared upon.

        Raises:
            UnsupportedType: If the DTO type does not support the annotated type of ``parsed_type``.
        """
