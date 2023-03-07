from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine

    from starlite._signature.models import SignatureField
    from starlite.connection import ASGIConnection, Request

    from .abc import AbstractDTO

__all__ = ("create_dto_extractor",)


def create_dto_extractor(
    signature_field: SignatureField,
) -> Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]:
    """Create a DTO data extractor.

    Args:
        signature_field: A SignatureField instance.

    Returns:
        An extractor function.
    """
    dto_type = cast("type[AbstractDTO[Any]]", signature_field.parsed_parameter.annotation)
    is_dto_supported = signature_field.parsed_parameter.dto_supported

    async def dto_extractor(connection: Request[Any, Any, Any]) -> Any:
        dto = dto_type.from_bytes(await connection.body())
        if is_dto_supported:
            return dto.data
        return dto

    return dto_extractor  # type:ignore[return-value]
