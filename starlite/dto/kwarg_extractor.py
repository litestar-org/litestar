from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine

    from starlite._signature.models import SignatureField
    from starlite.connection import ASGIConnection, Request

    from .abc import AbstractDTOInterface

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
    dto_type = signature_field.parsed_parameter.dto or cast(
        "type[AbstractDTOInterface]", signature_field.parsed_parameter.annotation
    )
    is_not_dto_annotated = bool(signature_field.parsed_parameter.dto)

    async def dto_extractor(connection: Request[Any, Any, Any]) -> Any:
        dto = dto_type.from_bytes(await connection.body())
        if is_not_dto_annotated:
            return dto.get_data()
        return dto

    return dto_extractor  # type:ignore[return-value]
