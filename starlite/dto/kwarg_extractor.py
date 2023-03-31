from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine

    from starlite._signature.models import SignatureField
    from starlite.connection import ASGIConnection, Request

    from .abc import AbstractDTOInterface

__all__ = ("create_dto_extractor",)


def create_dto_extractor(
    signature_field: SignatureField, dto_type: type[AbstractDTOInterface]
) -> Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]:
    """Create a DTO data extractor.

    Args:
        signature_field: A SignatureField instance.
        dto_type: The :class:`AbstractDTOInterface` subclass.

    Returns:
        An extractor function.
    """
    is_dto_annotated = signature_field.has_dto_annotation

    async def dto_extractor(connection: Request[Any, Any, Any]) -> Any:
        dto = await dto_type.from_connection(connection)
        if is_dto_annotated:
            return dto
        return dto.to_data_type()

    return dto_extractor  # type:ignore[return-value]
