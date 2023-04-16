from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from typing_extensions import Self

    from litestar.connection import Request
    from litestar.enums import RequestEncodingType
    from litestar.handlers import BaseRouteHandler
    from litestar.openapi.spec import RequestBody, Schema
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
    def to_encodable_type(self) -> bytes | LitestarEncodableType:
        """Encode data held by the DTO type to a type supported by litestar serialization.

        Can return either bytes or a type that Litestar can return to bytes.

        Returns:
            Either ``bytes`` or a type that Litestar can convert to bytes.
        """

    @classmethod
    @abstractmethod
    def from_bytes(cls, raw: bytes, connection: Request[Any, Any, Any]) -> Self:
        """Construct an instance from a :class:`Request <.connection.Request>`.

        Args:
            raw: Raw bytes of the payload.
            connection: :class:`Request <.connection.Request>` instance.

        Returns:
            DTOInterface instance.
        """

    @classmethod
    @abstractmethod
    def from_data(cls, data: Any, connection: Request[Any, Any, Any]) -> Self:
        """Construct an instance from data.

        Args:
            data: User data, usually data returned from a handler.
            connection: :class:`Request <.connection.Request>` instance.

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
        return

    @classmethod
    def create_openapi_request_body(
        cls,
        handler: BaseRouteHandler,
        generate_examples: bool,
        media_type: RequestEncodingType | str,
        schemas: dict[str, Schema],
    ) -> RequestBody | None:
        """Create an OpenAPI request body for the DTO.

        Returns:
            An optional :class:`RequestBody <.openapi.spec.request_body.RequestBody>` instance.
        """
        return None
