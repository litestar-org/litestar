from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from litestar.openapi.spec import Schema

if TYPE_CHECKING:
    from litestar.enums import RequestEncodingType
    from litestar.handlers import BaseRouteHandler
    from litestar.openapi.spec import Reference
    from litestar.types import LitestarEncodableType
    from litestar.types.internal_types import AnyConnection
    from litestar.utils.signature import ParsedType

    from .types import ForType

__all__ = ("DTOInterface", "HandlerContext")


class HandlerContext:
    """Context object passed to the ``on_registration`` method of a DTO."""

    __slots__ = ("dto_for", "route_handler", "parsed_type", "request_encoding_type")

    def __init__(
        self,
        dto_for: ForType,
        route_handler: BaseRouteHandler,
        parsed_type: ParsedType,
        request_encoding_type: RequestEncodingType | str | None = None,
    ) -> None:
        self.dto_for: ForType = dto_for
        self.route_handler = route_handler
        self.parsed_type = parsed_type
        self.request_encoding_type = request_encoding_type


@runtime_checkable
class DTOInterface(Protocol):
    __slots__ = ()

    @abstractmethod
    def __init__(self, connection: AnyConnection) -> None:
        """Initialize the DTO.

        Args:
            connection: :class:`ASGIConnection <.connection.ASGIConnection>` instance.
        """

    @abstractmethod
    def data_to_encodable_type(self, data: Any) -> bytes | LitestarEncodableType:
        """Encode data to a type supported by litestar serialization.

        Can return either bytes or a type that Litestar can return to bytes.

        Returns:
            Either ``bytes`` or a type that Litestar can convert to bytes.
        """

    @abstractmethod
    def builtins_to_data_type(self, builtins: Any) -> Any:
        """Convert unstructured data to the data type that the DTO represents.

        Args:
            builtins: unstructured data parsed from the payload.

        Returns:
            Data type that the DTO represents.
        """

    @abstractmethod
    def bytes_to_data_type(self, raw: bytes) -> Any:
        """Convert raw bytes to the data type that the DTO represents.

        Args:
            raw: Raw bytes of the payload.

        Returns:
            Data type that the DTO represents.
        """

    @classmethod
    def create_openapi_schema(
        cls,
        dto_for: ForType,
        handler: BaseRouteHandler,
        generate_examples: bool,
        schemas: dict[str, Schema],
    ) -> Reference | Schema:
        """Create an OpenAPI request body for the DTO.

        Returns:
            An optional :class:`RequestBody <.openapi.spec.request_body.RequestBody>` instance.
        """
        return Schema()

    @classmethod
    def on_registration(cls, handler_context: HandlerContext) -> None:
        """Receive the ``parsed_type`` and ``route_handler`` that this DTO is configured to represent.

        At this point, if the DTO type does not support the annotated type of ``parsed_type``, it should raise an
        ``UnsupportedType`` exception.

        Args:
            handler_context: A :class:`HandlerContext <.HandlerContext>` instance. Provides information about the
                handler and application of the DTO.

        Raises:
            UnsupportedType: If the DTO type does not support the annotated type of ``parsed_type``.
        """
        return
